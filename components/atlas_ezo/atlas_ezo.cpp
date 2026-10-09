#include "atlas_ezo.h"
#include "esphome/core/log.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include <cctype>
#include <cstdlib>
#include <cstring>

namespace esphome {
namespace atlas_ezo {

static const char *const TAG = "atlas_ezo";
static const uart_port_t UART = UART_NUM_2;
static const uint32_t I2C_HALF_US = 40;

static std::string upper_copy(std::string text) {
  for (char &c : text) {
    c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
  }
  return text;
}

static std::string trim_copy(const std::string &text) {
  size_t begin = 0;
  while (begin < text.size() && std::isspace(static_cast<unsigned char>(text[begin]))) {
    begin++;
  }
  size_t end = text.size();
  while (end > begin && std::isspace(static_cast<unsigned char>(text[end - 1]))) {
    end--;
  }
  return text.substr(begin, end - begin);
}

static std::vector<std::string> split_csv(const std::string &text) {
  std::vector<std::string> out;
  std::string cur;
  for (char c : text) {
    if (c == ',') {
      out.push_back(trim_copy(cur));
      cur.clear();
    } else {
      cur.push_back(c);
    }
  }
  out.push_back(trim_copy(cur));
  return out;
}

std::string AtlasEzo::canon_(const std::string &token) {
  const std::string u = upper_copy(token);
  if (u == "PH") {
    return "PH";
  }
  if (u == "OR" || u == "ORP") {
    return "OR";
  }
  if (u == "EC") {
    return "EC";
  }
  if (u == "RTD") {
    return "RTD";
  }
  if (u == "DO") {
    return "DO";
  }
  return u;
}

std::string AtlasEzo::display_(const std::string &kind) {
  if (kind == "PH") {
    return "pH";
  }
  if (kind == "OR") {
    return "ORP";
  }
  if (kind == "EC") {
    return "EC";
  }
  if (kind == "RTD") {
    return "RTD";
  }
  if (kind == "DO") {
    return "DO";
  }
  if (kind.empty()) {
    return "none";
  }
  return kind;
}

void AtlasEzo::add_port(InternalGPIOPin *tx, InternalGPIOPin *rx) {
  if (this->count_ >= 3) {
    return;
  }
  this->ports_[this->count_].tx = tx;
  this->ports_[this->count_].rx = rx;
  this->count_++;
}

void AtlasEzo::set_socket_sensor(uint8_t index, text_sensor::TextSensor *sensor) {
  if (index < 3) {
    this->ports_[index].label = sensor;
  }
}

void AtlasEzo::dump_config() {
  ESP_LOGCONFIG(TAG, "Atlas sockets: %u", this->count_);
  if (this->disabled_) {
    ESP_LOGCONFIG(TAG, "  UART2 unavailable");
  }
}

void AtlasEzo::setup() {
  for (uint8_t i = 0; i < this->count_; i++) {
    this->ports_[i].tx->setup();
    this->ports_[i].rx->setup();
  }
  uart_config_t cfg{};
  cfg.baud_rate = 9600;
  cfg.data_bits = UART_DATA_8_BITS;
  cfg.parity = UART_PARITY_DISABLE;
  cfg.stop_bits = UART_STOP_BITS_1;
  cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
  cfg.source_clk = UART_SCLK_DEFAULT;
  if (uart_driver_install(UART, 512, 256, 0, nullptr, 0) != ESP_OK || uart_param_config(UART, &cfg) != ESP_OK) {
    ESP_LOGE(TAG, "Could not install UART2");
    this->disabled_ = true;
    return;
  }
  this->release_uart_();
  this->next_action_ = millis() + 1000;
}

void AtlasEzo::detach_other_pins_(const Port &active) {
  for (uint8_t i = 0; i < this->count_; i++) {
    if (&this->ports_[i] == &active) {
      continue;
    }
    gpio_reset_pin(static_cast<gpio_num_t>(this->ports_[i].tx->get_pin()));
    gpio_reset_pin(static_cast<gpio_num_t>(this->ports_[i].rx->get_pin()));
  }
}

void AtlasEzo::attach_uart_(Port &port) {
  this->scanning_ = false;
  this->detach_other_pins_(port);
  uart_set_pin(UART, port.tx->get_pin(), port.rx->get_pin(), UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
  uart_flush_input(UART);
}

void AtlasEzo::release_uart_() {}

void AtlasEzo::arm_i2c_(Port &port) {
  this->detach_other_pins_(port);
  gpio_reset_pin(static_cast<gpio_num_t>(port.tx->get_pin()));
  gpio_reset_pin(static_cast<gpio_num_t>(port.rx->get_pin()));
  const gpio::Flags mode = gpio::FLAG_INPUT | gpio::FLAG_OUTPUT | gpio::FLAG_OPEN_DRAIN | gpio::FLAG_PULLUP;
  // EZO TX is SDA, which is this socket's RX pin. EZO RX is SCL.
  port.rx->pin_mode(mode);
  port.tx->pin_mode(mode);
  port.rx->digital_write(true);
  port.tx->digital_write(true);
}

void AtlasEzo::send_uart_(const char *text, uint32_t wait_ms) {
  this->buffer_.clear();
  this->line_ready_ = false;
  this->waiting_ = true;
  this->i2c_wait_ = false;
  uart_write_bytes(UART, text, strlen(text));
  this->deadline_ = millis() + wait_ms;
}

void AtlasEzo::show_(Port &port, const std::string &text) {
  if (port.label == nullptr || port.shown == text) {
    return;
  }
  port.shown = text;
  port.label->publish_state(text);
}

void AtlasEzo::clear_port_(Port &port) {
  port.identified = false;
  port.kind.clear();
  port.fields.clear();
  port.outputs_known = false;
  port.have_read = false;
  port.nvalues = 0;
  port.address = 0;
  port.uart_mode = true;
  this->show_(port, "none");
}

bool AtlasEzo::parse_info_(const std::string &line, std::string &kind) {
  const auto fields = split_csv(line);
  if (fields.size() < 2) {
    return false;
  }
  const std::string head = upper_copy(fields[0]);
  if (head.find('I') == std::string::npos || head.find('O') != std::string::npos) {
    return false;
  }
  kind = canon_(fields[1]);
  return !kind.empty();
}

bool AtlasEzo::parse_outputs_(const std::string &line) {
  const auto fields = split_csv(line);
  if (fields.empty()) {
    return false;
  }
  const std::string head = upper_copy(fields[0]);
  if (head.find('O') == std::string::npos) {
    return false;
  }
  Port &port = this->ports_[this->index_];
  port.fields.clear();
  for (size_t i = 1; i < fields.size(); i++) {
    if (!fields[i].empty()) {
      port.fields.push_back(upper_copy(fields[i]));
    }
  }
  port.outputs_known = !port.fields.empty();
  return port.outputs_known;
}

bool AtlasEzo::parse_reading_(const std::string &line) {
  if (line.empty() || line[0] == '*' || line[0] == '?') {
    return false;
  }
  Port &port = this->ports_[this->index_];
  const auto fields = split_csv(line);
  port.nvalues = 0;
  for (const auto &field : fields) {
    if (port.nvalues >= 4 || field.empty()) {
      continue;
    }
    char *end = nullptr;
    const float value = strtof(field.c_str(), &end);
    if (end == field.c_str()) {
      continue;
    }
    port.values[port.nvalues++] = value;
  }
  if (!port.outputs_known && port.kind == "EC") {
    if (port.nvalues >= 4) {
      port.fields = {"EC", "TDS", "S", "SG"};
    } else if (port.nvalues == 1) {
      port.fields = {"EC"};
    }
    port.outputs_known = !port.fields.empty();
  }
  port.have_read = port.nvalues > 0;
  return port.have_read;
}

static void sda_set(InternalGPIOPin *pin, bool high) { pin->digital_write(high); }

static void i2c_delay() { delayMicroseconds(I2C_HALF_US); }

static void i2c_start(InternalGPIOPin *sda, InternalGPIOPin *scl) {
  sda_set(sda, true);
  sda_set(scl, true);
  i2c_delay();
  sda_set(sda, false);
  i2c_delay();
  sda_set(scl, false);
}

static void i2c_stop(InternalGPIOPin *sda, InternalGPIOPin *scl) {
  sda_set(sda, false);
  i2c_delay();
  sda_set(scl, true);
  i2c_delay();
  sda_set(sda, true);
  i2c_delay();
}

static bool i2c_write_byte(InternalGPIOPin *sda, InternalGPIOPin *scl, uint8_t data) {
  for (int bit = 0; bit < 8; bit++) {
    sda_set(scl, false);
    sda_set(sda, (data & 0x80) != 0);
    i2c_delay();
    sda_set(scl, true);
    i2c_delay();
    data <<= 1;
  }
  sda_set(scl, false);
  sda_set(sda, true);
  i2c_delay();
  sda_set(scl, true);
  i2c_delay();
  const bool ack = !sda->digital_read();
  sda_set(scl, false);
  return ack;
}

static bool i2c_read_byte(InternalGPIOPin *sda, InternalGPIOPin *scl, uint8_t &data, bool ack) {
  data = 0;
  sda_set(sda, true);
  for (int bit = 0; bit < 8; bit++) {
    sda_set(scl, false);
    i2c_delay();
    sda_set(scl, true);
    i2c_delay();
    data = static_cast<uint8_t>((data << 1) | (sda->digital_read() ? 1 : 0));
  }
  sda_set(scl, false);
  sda_set(sda, !ack);
  i2c_delay();
  sda_set(scl, true);
  i2c_delay();
  sda_set(scl, false);
  sda_set(sda, true);
  return true;
}

bool AtlasEzo::i2c_probe_(Port &port, uint8_t address) {
  InternalGPIOPin *sda = port.rx;
  InternalGPIOPin *scl = port.tx;
  i2c_start(sda, scl);
  const bool ack = i2c_write_byte(sda, scl, static_cast<uint8_t>(address << 1));
  i2c_stop(sda, scl);
  return ack;
}

void AtlasEzo::i2c_write_(Port &port, uint8_t address, const char *text) {
  InternalGPIOPin *sda = port.rx;
  InternalGPIOPin *scl = port.tx;
  i2c_start(sda, scl);
  if (!i2c_write_byte(sda, scl, static_cast<uint8_t>(address << 1))) {
    i2c_stop(sda, scl);
    return;
  }
  for (const char *p = text; *p != '\0'; p++) {
    i2c_write_byte(sda, scl, static_cast<uint8_t>(*p));
  }
  i2c_stop(sda, scl);
}

std::string AtlasEzo::i2c_read_(Port &port, uint8_t address) {
  InternalGPIOPin *sda = port.rx;
  InternalGPIOPin *scl = port.tx;
  i2c_start(sda, scl);
  if (!i2c_write_byte(sda, scl, static_cast<uint8_t>((address << 1) | 1))) {
    i2c_stop(sda, scl);
    return "";
  }
  uint8_t code = 0;
  i2c_read_byte(sda, scl, code, true);
  std::string out;
  for (int i = 0; i < 31; i++) {
    uint8_t byte = 0;
    i2c_read_byte(sda, scl, byte, i < 30);
    if (byte == 0) {
      break;
    }
    if (byte >= 32) {
      out.push_back(static_cast<char>(byte));
    }
  }
  i2c_stop(sda, scl);
  return out;
}

void AtlasEzo::begin_port_() {
  if (this->index_ >= this->count_) {
    this->publish_();
    this->index_ = 0;
    this->next_action_ = millis() + 2000;
    return;
  }
  Port &port = this->ports_[this->index_];
  if (!port.identified) {
    this->job_ = Job::INFO;
  } else if (port.kind == "EC" && !port.outputs_known) {
    this->job_ = Job::OUTPUTS;
  } else {
    this->job_ = Job::READ;
  }
  if (!port.uart_mode && port.address != 0) {
    this->arm_i2c_(port);
    this->scanning_ = false;
    this->issue_();
    return;
  }
  if (!port.uart_mode) {
    this->arm_i2c_(port);
    this->scan_address_ = 1;
    this->scanning_ = true;
    this->waiting_ = false;
    return;
  }
  this->attach_uart_(port);
  this->issue_();
}

void AtlasEzo::issue_() {
  Port &port = this->ports_[this->index_];
  if (port.uart_mode) {
    if (this->job_ == Job::INFO) {
      this->send_uart_("i\r", 400);
    } else if (this->job_ == Job::OUTPUTS) {
      this->send_uart_("O,?\r", 400);
    } else {
      this->send_uart_("R\r", 1200);
    }
    return;
  }
  const char *text = "R";
  if (this->job_ == Job::INFO) {
    text = "i";
  } else if (this->job_ == Job::OUTPUTS) {
    text = "O,?";
  }
  this->i2c_write_(port, port.address, text);
  this->waiting_ = true;
  this->i2c_wait_ = true;
  this->line_ready_ = false;
  this->buffer_.clear();
  this->deadline_ = millis() + (this->job_ == Job::READ ? 1000 : 350);
}

void AtlasEzo::on_line_(const std::string &line) {
  Port &port = this->ports_[this->index_];
  this->waiting_ = false;
  if (!line.empty() && line[0] == '*' && line.find("OK") != std::string::npos) {
    this->waiting_ = true;
    this->deadline_ = millis() + 300;
    return;
  }
  if (this->job_ == Job::INFO) {
    std::string kind;
    if (!this->parse_info_(line, kind)) {
      this->on_timeout_();
      return;
    }
    if (port.kind != kind) {
      port.fields.clear();
      port.outputs_known = false;
      port.have_read = false;
      ESP_LOGI(TAG, "Socket %u is %s", this->index_ + 1, display_(kind).c_str());
    }
    port.kind = kind;
    port.identified = true;
    port.misses = 0;
    this->show_(port, display_(kind));
    this->job_ = (kind == "EC") ? Job::OUTPUTS : Job::READ;
    this->issue_();
    return;
  }
  if (this->job_ == Job::OUTPUTS) {
    if (!this->parse_outputs_(line)) {
      this->on_timeout_();
      return;
    }
    port.misses = 0;
    this->job_ = Job::READ;
    this->issue_();
    return;
  }
  if (!this->parse_reading_(line)) {
    this->on_timeout_();
    return;
  }
  port.misses = 0;
  this->advance_();
}

void AtlasEzo::on_timeout_() {
  Port &port = this->ports_[this->index_];
  this->waiting_ = false;
  port.misses++;
  if (port.uart_mode && port.misses >= 2) {
    port.uart_mode = false;
    port.misses = 0;
    this->arm_i2c_(port);
    this->scan_address_ = 1;
    this->scanning_ = true;
    return;
  }
  if (!port.uart_mode && port.misses >= 2) {
    this->clear_port_(port);
    port.uart_mode = true;
  }
  this->advance_();
}

void AtlasEzo::advance_() {
  this->waiting_ = false;
  this->scanning_ = false;
  this->index_++;
  this->next_action_ = millis() + 50;
}

void AtlasEzo::publish_() {
  float ph = NAN, orp = NAN, cond = NAN, tds = NAN, sal = NAN, rtd = NAN, dissolved = NAN;
  bool have_ph = false, have_orp = false, have_cond = false, have_tds = false, have_sal = false, have_rtd = false,
       have_do = false;
  for (uint8_t i = 0; i < this->count_; i++) {
    Port &port = this->ports_[i];
    if (!port.have_read) {
      continue;
    }
    if (port.kind == "PH" && !have_ph) {
      ph = port.values[0];
      have_ph = true;
    } else if (port.kind == "OR" && !have_orp) {
      orp = port.values[0];
      have_orp = true;
    } else if (port.kind == "RTD" && !have_rtd) {
      rtd = port.values[0] * 1.8f + 32.0f;
      have_rtd = true;
    } else if (port.kind == "DO" && !have_do) {
      dissolved = port.values[0];
      have_do = true;
    } else if (port.kind == "EC") {
      uint8_t n = 0;
      for (const auto &field : port.fields) {
        if (n >= port.nvalues) {
          break;
        }
        const float value = port.values[n++];
        if (field == "EC" && !have_cond) {
          cond = value;
          have_cond = true;
        } else if (field == "TDS" && !have_tds) {
          tds = value;
          have_tds = true;
        } else if (field == "S" && !have_sal) {
          sal = value;
          have_sal = true;
        }
      }
    }
  }
  auto put = [](sensor::Sensor *sensor, bool have, bool &saw, float value) {
    if (sensor == nullptr) {
      return;
    }
    if (have) {
      sensor->publish_state(value);
      saw = true;
    } else if (saw) {
      sensor->publish_state(NAN);
      saw = false;
    }
  };
  put(this->ph_, have_ph, this->saw_ph_, ph);
  put(this->orp_, have_orp, this->saw_orp_, orp);
  put(this->conductivity_, have_cond, this->saw_cond_, cond);
  put(this->tds_, have_tds, this->saw_tds_, tds);
  put(this->salinity_, have_sal, this->saw_sal_, sal);
  put(this->rtd_, have_rtd, this->saw_rtd_, rtd);
  put(this->dissolved_oxygen_, have_do, this->saw_do_, dissolved);
}

void AtlasEzo::pump_uart_() {
  uint8_t byte = 0;
  while (uart_read_bytes(UART, &byte, 1, 0) == 1) {
    if (byte == '\r') {
      this->line_ready_ = true;
      this->waiting_ = false;
      return;
    }
    if (byte >= 32 && this->buffer_.size() < 80) {
      this->buffer_.push_back(static_cast<char>(byte));
    }
  }
}

void AtlasEzo::loop() {
  if (this->disabled_) {
    return;
  }
  if (this->scanning_) {
    Port &port = this->ports_[this->index_];
    if (this->i2c_probe_(port, this->scan_address_)) {
      port.address = this->scan_address_;
      port.uart_mode = false;
      port.identified = false;
      this->scanning_ = false;
      this->job_ = Job::INFO;
      ESP_LOGI(TAG, "Socket %u answered I2C %u", this->index_ + 1, port.address);
      this->issue_();
      return;
    }
    if (++this->scan_address_ > 127) {
      this->clear_port_(port);
      port.uart_mode = true;
      this->advance_();
    }
    return;
  }
  if (this->waiting_ && this->i2c_wait_) {
    if (static_cast<int32_t>(millis() - this->deadline_) < 0) {
      return;
    }
    Port &port = this->ports_[this->index_];
    const std::string line = this->i2c_read_(port, port.address);
    this->i2c_wait_ = false;
    this->waiting_ = false;
    if (line.empty()) {
      this->on_timeout_();
    } else {
      this->on_line_(line);
    }
    return;
  }
  if (this->waiting_) {
    this->pump_uart_();
    if (this->line_ready_) {
      const std::string line = this->buffer_;
      this->buffer_.clear();
      this->line_ready_ = false;
      this->on_line_(line);
      return;
    }
    if (static_cast<int32_t>(millis() - this->deadline_) >= 0) {
      this->on_timeout_();
    }
    return;
  }
  if (static_cast<int32_t>(millis() - this->next_action_) < 0) {
    return;
  }
  this->begin_port_();
}

}  // namespace atlas_ezo
}  // namespace esphome
