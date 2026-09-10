#include "pentair_if_ic.h"
#include "esphome/core/log.h"
#include <cinttypes>
#include <cstdio>
#include <string>

namespace esphome {
namespace pentair_if_ic {

static const char *TAG = "pentair_if_ic";

namespace {

const char *if_run_state_name(uint8_t value) {
  switch (value) {
    case STOPPED:
      return "stopped";
    case RUNNING:
      return "running";
    default:
      return "unknown";
  }
}

const char *if_program_name(uint8_t value) {
  switch (value) {
    case NO_PROG:
      return "none";
    case LOCAL1:
      return "Local 1";
    case LOCAL2:
      return "Local 2";
    case LOCAL3:
      return "Local 3";
    case LOCAL4:
      return "Local 4";
    case EXT1:
      return "External 1";
    case EXT2:
      return "External 2";
    case EXT3:
      return "External 3";
    case EXT4:
      return "External 4";
    case TIMEOUT:
      return "Time Out";
    case PRIMING:
      return "Priming";
    case QUICKCLEAN:
      return "Quick Clean";
    default:
      return "unknown";
  }
}

std::string ic_alarm_text(uint8_t error_field) {
  if (error_field == 0) {
    return "no alarms";
  }
  std::string out;
  auto add = [&](bool bit, const char *name) {
    if (!bit) {
      return;
    }
    if (!out.empty()) {
      out += ", ";
    }
    out += name;
  };
  add(GETBIT8(error_field, 0), "no flow");
  add(GETBIT8(error_field, 1), "low salt");
  add(GETBIT8(error_field, 2), "high salt");
  add(GETBIT8(error_field, 3), "clean cell");
  add(GETBIT8(error_field, 4), "high current");
  add(GETBIT8(error_field, 5), "low voltage");
  add(GETBIT8(error_field, 6), "low temperature");
  add(GETBIT8(error_field, 7), "check PCB");
  return out.empty() ? "no alarms" : out;
}

std::string describe_if_packet(const std::vector<uint8_t> &raw) {
  const uint8_t *p = raw.data();
  size_t n = raw.size();
  if (n >= 4 && p[0] == 0xFF && p[1] == 0x00 && p[2] == 0xFF) {
    p += 3;
    n -= 3;
  }
  if (n < 6 || p[0] != 0xA5) {
    return "unrecognized pump packet";
  }

  const uint8_t src = p[3];
  const uint8_t action = p[4];
  const uint8_t len = p[5];
  const uint8_t *d = (n >= 6u + len) ? p + 6 : nullptr;
  const bool from_pump = (src == 0x60 || src == 0x61);
  char buf[192];

  switch (action) {
    case 0x01:
      if (d != nullptr && len >= 4 && d[0] == 0x02 && d[1] == 0xC4) {
        snprintf(buf, sizeof(buf), "set speed to %d RPM", (d[2] * 256) + d[3]);
        return buf;
      }
      if (d != nullptr && len >= 4 && d[0] == 0x03 && d[1] == 0x21) {
        snprintf(buf, sizeof(buf), "run external program %d", d[3] / 8);
        return buf;
      }
      if (d != nullptr && len >= 4 && d[0] == 0x03 && d[1] >= 0x26 && d[1] <= 0x2A) {
        snprintf(buf, sizeof(buf), "save %d RPM to program %d", (d[2] * 256) + d[3],
                 (d[1] - 0x26) + 1);
        return buf;
      }
      return "write pump setting";
    case 0x03:
      if (d != nullptr && len >= 2) {
        snprintf(buf, sizeof(buf), "set pump clock to %02u:%02u", (unsigned) d[0], (unsigned) d[1]);
        return buf;
      }
      return "set pump clock";
    case 0x04:
      if (d != nullptr && len >= 1) {
        if (d[0] == 0xFF) {
          return "request remote control";
        }
        if (d[0] == 0x00) {
          return "release to local control";
        }
      }
      return "set pump control mode";
    case 0x05:
      if (d != nullptr && len >= 1) {
        snprintf(buf, sizeof(buf), "run local program %u", (unsigned) d[0]);
        return buf;
      }
      return "run local program";
    case 0x06:
      if (d != nullptr && len >= 1) {
        if (d[0] == RUNNING) {
          return "run pump";
        }
        if (d[0] == STOPPED) {
          return "stop pump";
        }
      }
      return "set pump run/stop";
    case 0x07:
      if (from_pump) {
        if (n > 20) {
          snprintf(buf, sizeof(buf),
                   "pump status: %s, %d RPM, %d W, program %s, clock %02u:%02u",
                   if_run_state_name(p[6]), (p[11] * 256) + p[12], (p[9] * 256) + p[10],
                   if_program_name(p[7]), (unsigned) p[19], (unsigned) p[20]);
          return buf;
        }
        return "pump status";
      }
      return "request pump status";
    case 0x09:
      if (d != nullptr && len >= 4) {
        snprintf(buf, sizeof(buf), "set flow to %.1f m3/h", d[3] / 10.0);
        return buf;
      }
      return "set pump flow";
    case 0xFF:
      if (d != nullptr && len >= 1 && d[0] == 0x19) {
        return "pump rejected command (not supported on this model)";
      }
      return "pump reported an error";
    default:
      return "unrecognized pump packet";
  }
}

std::string describe_ic_packet(const std::vector<uint8_t> &raw) {
  if (raw.size() < 4) {
    return "incomplete chlorinator packet";
  }
  const uint8_t *p = raw.data();
  const size_t n = raw.size();
  char buf[192];

  switch (p[3]) {
    case 0x00:
      return "chlorinator takeover";
    case 0x01:
      return "chlorinator takeover reply";
    case 0x03: {
      std::string ver;
      for (int i = 5; i <= static_cast<int>(n) - 4; i++) {
        ver += static_cast<char>(p[i]);
      }
      if (ver.empty()) {
        return "chlorinator version reply";
      }
      snprintf(buf, sizeof(buf), "chlorinator version %s", ver.c_str());
      return buf;
    }
    case 0x11:
      if (n > 4) {
        snprintf(buf, sizeof(buf), "set chlorinator output to %u%%", (unsigned) p[4]);
        return buf;
      }
      return "set chlorinator output";
    case 0x12:
      if (n > 5) {
        snprintf(buf, sizeof(buf), "chlorinator status: %u ppm salt, %s",
                 (unsigned) p[4] * 50, ic_alarm_text(p[5]).c_str());
        return buf;
      }
      return "chlorinator status";
    case 0x14:
      return "request chlorinator version";
    case 0x15:
      return "request chlorinator temperature";
    case 0x16:
      if (n > 4) {
        snprintf(buf, sizeof(buf), "chlorinator temperature %u °F", (unsigned) p[4]);
        return buf;
      }
      return "chlorinator temperature";
    default:
      return "unrecognized chlorinator packet";
  }
}

}  // namespace

void PentairIfIcComponent::setup() {
  ESP_LOGCONFIG(TAG, "Setting up Pentair IntelliFlo%s...",
                this->enable_intellichlor_ ? " + IntelliChlor" : " (IntelliChlor disabled)");

  if (this->enable_intellichlor_) {
    this->read_all_chlorinator_info();
    ESP_LOGCONFIG(TAG, "IntelliChlor Version: %s", this->ic_version_.c_str());
  }
  
  if (this->flow_control_pin_ != nullptr) {
    ESP_LOGCONFIG(TAG, "Using Flow Control");
    this->flow_control_pin_->setup();
  }
  
  this->ic_last_command_timestamp_ = millis();
  this->ic_last_recv_timestamp_ = millis();
  this->ic_last_loop_timestamp_ = millis() - 31000;  // Allow immediate first poll
  this->last_received_byte_millis_ = millis();
}

void PentairIfIcComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "Pentair IntelliFlo + IntelliChlor RS485 Component");
  ESP_LOGCONFIG(TAG, "  IntelliChlor polling: %s", YESNO(this->enable_intellichlor_));

  // IntelliChlor sensors
  LOG_TEXT_SENSOR("  ", "IC_VersionTextSensor", this->ic_version_text_sensor_);
  LOG_SWITCH("  ", "TakeoverModeSwitch", this->takeover_mode_switch_);
  LOG_NUMBER("  ", "SWGPercentNumber", this->swg_percent_number_);
  LOG_SENSOR("  ", "WaterTempSensor", this->water_temp_sensor_);
  LOG_SENSOR("  ", "SaltPPMSensor", this->salt_ppm_sensor_);
  LOG_SENSOR("  ", "IC_ErrorSensor", this->ic_error_sensor_);
  LOG_SENSOR("  ", "IC_StatusSensor", this->ic_status_sensor_);
  
  // IntelliFlo sensors
  LOG_SENSOR("  ", "IF_PowerSensor", this->if_power_);
  LOG_SENSOR("  ", "IF_RPMSensor", this->if_rpm_);
  LOG_BINARY_SENSOR("  ", "IF_RunningBinarySensor", this->if_running_);
  LOG_TEXT_SENSOR("  ", "IF_ProgramTextSensor", this->if_program_);
  
  LOG_PIN("  Flow Control Pin: ", this->flow_control_pin_);
}

void PentairIfIcComponent::loop() {
  // Read all bytes from UART into common buffer
  while (this->available() > 0) {
    uint8_t c;
    this->read_byte(&c);
    this->last_received_byte_millis_ = millis();
    ESP_LOGV(TAG, "Received byte: %02X, buffer size: %d", c, this->rx_buffer_.size());
    
    // Check if we're currently building a packet
    if (!this->rx_buffer_.empty()) {
      // Continue building current packet (either IntelliFlo or IntelliChlor)
      this->rx_buffer_.push_back(c);
      
      // Try to parse based on first byte
      if (this->rx_buffer_[0] == 0xFF) {
        // IntelliFlo packet
        ESP_LOGV(TAG, "Validating IF packet, buffer size: %d", this->rx_buffer_.size());
        if (!this->validate_if_received_message_()) {
          this->rx_buffer_.clear();
        }
      } else if (this->rx_buffer_[0] == 0x10) {
        // IntelliChlor packet
        ESP_LOGV(TAG, "Parsing IC packet, buffer size: %d", this->rx_buffer_.size());
        if (!this->parse_ic_packet_()) {
          // Continue building
        } else {
          // Packet complete, clear buffer
          this->rx_buffer_.clear();
        }
      } else {
        // Invalid packet start
        ESP_LOGW(TAG, "RS485 noise, dropped packet");
        this->rx_buffer_.clear();
      }
    }
    // Start new packet - determine type by first byte
    else if (c == 0xFF || c == 0x10) {
      // Start new packet (IntelliFlo or IntelliChlor)
      ESP_LOGD(TAG, "Starting %s packet", c == 0xFF ? "IntelliFlo" : "IntelliChlor");
      this->rx_buffer_.push_back(c);
    }
    // Unknown/noise - ignore
    else {
      ESP_LOGV(TAG, "Ignoring unexpected byte: %02X", c);
    }
  }
  
  // IntelliChlor processing - only from update(), not from loop()
  // Remove ic_run_again_ logic to prevent rapid polling
  
  // Process unified send queue
  auto since_last_cmd = millis() - this->ic_last_command_timestamp_;
  auto since_last_tx = millis() - this->last_tx_millis_;
  auto since_last_rx = millis() - this->last_received_byte_millis_;
  
  // Only send if enough time has passed since ANY transmission
  if (since_last_cmd > 100 && since_last_tx > 150 && since_last_rx > 100) {
    if (!this->tx_queue_.empty()) {
      auto packet = this->tx_queue_.front();
      auto type = std::get<0>(packet);
      auto retries = std::get<1>(packet);
      auto attempts = std::get<2>(packet);
      auto data = std::get<3>(packet);
      
      attempts++;
      
      if (type == PACKET_TYPE_IC) {
        ESP_LOGD(TAG, "IC Process Queue Retries:%i Attempt:%i", retries, attempts);
        
        if (attempts > retries) {
          ESP_LOGE(TAG, "IC No response %i > %i removing from send queue", retries, attempts);
          this->tx_queue_.pop();
        } else {
          // Update attempts
          std::get<2>(this->tx_queue_.front()) = attempts;
          
          if (this->flow_control_pin_ != nullptr) {
            ESP_LOGV(TAG, "Enable Send");
            this->flow_control_pin_->digital_write(true);
          }
          
          ESP_LOGV(TAG, "IC Sent: %s", format_hex_pretty(data).c_str());
          ESP_LOGI(TAG, "IC sent: %s", describe_ic_packet(data).c_str());
          this->write_array(data);
          this->flush();
          
          if (this->flow_control_pin_ != nullptr) {
            ESP_LOGV(TAG, "Disable Send");
            this->flow_control_pin_->digital_write(false);
          }
          
          this->ic_last_command_timestamp_ = millis();
          this->last_tx_millis_ = millis();
        }
      } else if (type == PACKET_TYPE_IF) {
        // IntelliFlo packet - send immediately and remove from queue
        this->flush();
        this->write_array(&data[0], data.size());
        
        ESP_LOGV(TAG, "IF Sent: %s", format_hex_pretty(data).c_str());
        ESP_LOGI(TAG, "IF sent: %s", describe_if_packet(data).c_str());
        
        this->last_received_byte_millis_ = millis();
        this->last_tx_millis_ = millis();
        this->tx_queue_.pop();
      }
    }
  }
}

void PentairIfIcComponent::update() {
  // Status only. Do not send pumpToLocalControl() here — that packet
  // unlocks the IntelliFlo keypad and the pump then ignores ESP run/RPM until
  // remote control is taken again. After an ESP reboot the 30s poll was putting
  // the pump back in local mode even while Auto schedule was trying to run it.
  if (this->enable_intellichlor_) {
    this->read_all_chlorinator_info();
    this->set_timeout(500, [this]() { this->requestPumpStatus(); });
    return;
  }

  this->requestPumpStatus();
}

// ========================================
// IntelliChlor Methods
// ========================================

void PentairIfIcComponent::read_all_chlorinator_info() {
  if (!this->enable_intellichlor_) {
    return;
  }
  if (millis() - this->ic_last_loop_timestamp_ > 25000) {
    this->ic_last_loop_timestamp_ = millis();
    
    if (this->takeover_mode_switch_ != nullptr && this->takeover_mode_switch_->state) {
      this->ic_takeover_();
      if (this->swg_percent_number_ != nullptr) {
        this->ic_set_percent_(this->swg_percent_number_->state);
      }
    }
    this->get_ic_version_();
    this->get_ic_temp_();
    this->get_ic_more_();
  }
}

void PentairIfIcComponent::refresh_chlorinator() {
  if (!this->enable_intellichlor_) {
    ESP_LOGD(TAG, "IntelliChlor disabled; ignoring refresh");
    return;
  }
  // Force immediate refresh, bypassing rate limiting
  ESP_LOGD(TAG, "Manual chlorinator refresh requested");
  this->ic_last_loop_timestamp_ = millis();
  
  if (this->takeover_mode_switch_ != nullptr && this->takeover_mode_switch_->state) {
    this->ic_takeover_();
    if (this->swg_percent_number_ != nullptr) {
      this->ic_set_percent_(this->swg_percent_number_->state);
    }
  }
  this->get_ic_version_();
  this->get_ic_temp_();
  this->get_ic_more_();
}

void PentairIfIcComponent::set_swg_percent() {
  if (this->takeover_mode_switch_ != nullptr && this->takeover_mode_switch_->state) {
    this->read_all_chlorinator_info();
  }
}

void PentairIfIcComponent::set_takeover_mode(bool enable) {
  this->read_all_chlorinator_info();
}

void PentairIfIcComponent::get_ic_more_() {
  // Placeholder for additional commands
}

void PentairIfIcComponent::get_ic_version_() {
  uint8_t cmd[3] = {0x50, 0x14, 0x00};
  ESP_LOGD(TAG, "IC send GetVersion");
  this->send_ic_command_(cmd, 3, 1);
}

void PentairIfIcComponent::get_ic_temp_() {
  uint8_t cmd[3] = {0x50, 0x15, 0x00};
  ESP_LOGD(TAG, "IC send GetTemp");
  this->send_ic_command_(cmd, 3, 3);
}

void PentairIfIcComponent::ic_takeover_() {
  uint8_t cmd[3] = {0x50, 0x00, 0x00};
  ESP_LOGD(TAG, "IC send Takeover");
  this->send_ic_command_(cmd, 3, 3);
}

void PentairIfIcComponent::ic_set_percent_(uint8_t percent) {
  ESP_LOGD(TAG, "IC send SetPercent");
  this->ic_last_set_percent_ = percent;
  if (percent == 16) {
    uint8_t cmd[4] = {0x50, 0x11, percent, 0x00};
    this->send_ic_command_(cmd, 4, 3);
  } else {
    uint8_t cmd[3] = {0x50, 0x11, percent};
    this->send_ic_command_(cmd, 3, 3);
  }
}

void PentairIfIcComponent::send_ic_command_(const uint8_t *command, int command_len, uint8_t retries) {
  if (!this->enable_intellichlor_) {
    return;
  }
  uint8_t crc = 0;
  std::vector<uint8_t> packet;
  packet.reserve(command_len + 5);
  
  ESP_LOGD(TAG, "IC send_command_ Len:%i Retries:%i", command_len, retries);
  
  packet.push_back(IC_CMD_FRAME_HEADER[0]);
  crc += IC_CMD_FRAME_HEADER[0];
  
  packet.push_back(IC_CMD_FRAME_HEADER[1]);
  crc += IC_CMD_FRAME_HEADER[1];
  
  if (command != nullptr) {
    for (int i = 0; i < command_len; i++) {
      packet.push_back(command[i]);
      crc += command[i];
    }
  }
  
  packet.push_back(crc);
  packet.push_back(IC_CMD_FRAME_FOOTER[0]);
  packet.push_back(IC_CMD_FRAME_FOOTER[1]);
  
  this->tx_queue_.push(std::make_tuple(PACKET_TYPE_IC, retries, (uint8_t)0, packet));
}

bool PentairIfIcComponent::parse_ic_packet_() {
  size_t len = this->rx_buffer_.size();
  
  // Need at least header bytes
  if (len < 2) return false;
  
  // Validate header
  if (this->rx_buffer_[0] != 0x10) {
    ESP_LOGW(TAG, "IntelliChlor packet has a bad header, dropping");
    return true;  // Complete (invalid)
  }
  
  if (this->rx_buffer_[1] != 0x02) {
    // Still building
    if (len >= 64) {
      ESP_LOGW(TAG, "IntelliChlor packet too long, dropping");
      return true;  // Complete (error)
    }
    return false;
  }
  
  // Check for end marker: 0x10 0x03
  if (len >= 4) {
    for (size_t i = 2; i < len - 1; i++) {
      if (this->rx_buffer_[i] == 0x10 && this->rx_buffer_[i + 1] == 0x03) {
        // Complete IntelliChlor packet received
        this->ic_last_recv_timestamp_ = millis();
        
        ESP_LOGV(TAG, "IC Package received: %s", format_hex_pretty(this->rx_buffer_).c_str());
        ESP_LOGI(TAG, "IC received: %s", describe_ic_packet(this->rx_buffer_).c_str());
        
        uint8_t *buffer = &this->rx_buffer_[0];
        int pos = len - 1;
      
      if (pos >= 4 && buffer[3] == 0x03) {
        // Version response
        this->ic_version_ = "";
        for (int i = 5; i <= pos - 3; i++) {
          this->ic_version_ += buffer[i];
        }
        ESP_LOGD(TAG, "IC VersionResp: %s", this->ic_version_.c_str());
        if (this->ic_version_text_sensor_ != nullptr) {
          this->ic_version_text_sensor_->publish_state(this->ic_version_);
        }
      } else if (pos >= 4 && buffer[3] == 0x16) {
        // Temperature response
        auto temp = buffer[4];
        ESP_LOGD(TAG, "IC TempResp: %i", temp);
        if (this->water_temp_sensor_ != nullptr) {
          this->water_temp_sensor_->publish_state(temp);
        }
      } else if (pos >= 4 && buffer[3] == 0x12) {
        // Set response with salt and error
        uint16_t saltPPM = buffer[4] * 50;
        auto errorField = buffer[5];
        ESP_LOGD(TAG, "IC salt %u ppm, %s", saltPPM, ic_alarm_text(errorField).c_str());
        
        if (this->no_flow_binary_sensor_ != nullptr)
          this->no_flow_binary_sensor_->publish_state(GETBIT8(errorField, 0));
        if (this->low_salt_binary_sensor_ != nullptr)
          this->low_salt_binary_sensor_->publish_state(GETBIT8(errorField, 1));
        if (this->high_salt_binary_sensor_ != nullptr)
          this->high_salt_binary_sensor_->publish_state(GETBIT8(errorField, 2));
        if (this->clean_binary_sensor_ != nullptr)
          this->clean_binary_sensor_->publish_state(GETBIT8(errorField, 3));
        if (this->high_current_binary_sensor_ != nullptr)
          this->high_current_binary_sensor_->publish_state(GETBIT8(errorField, 4));
        if (this->low_volts_binary_sensor_ != nullptr)
          this->low_volts_binary_sensor_->publish_state(GETBIT8(errorField, 5));
        if (this->low_temp_binary_sensor_ != nullptr)
          this->low_temp_binary_sensor_->publish_state(GETBIT8(errorField, 6));
        if (this->check_pcb_binary_sensor_ != nullptr)
          this->check_pcb_binary_sensor_->publish_state(GETBIT8(errorField, 7));
        
        if (this->salt_ppm_sensor_ != nullptr)
          this->salt_ppm_sensor_->publish_state(saltPPM);
        if (this->ic_error_sensor_ != nullptr)
          this->ic_error_sensor_->publish_state(errorField);
        if (this->set_percent_sensor_ != nullptr)
          this->set_percent_sensor_->publish_state(this->ic_last_set_percent_);
      } else if (pos >= 4 && buffer[3] == 0x01) {
        // Takeover response
        auto status = buffer[3];
        ESP_LOGD(TAG, "IC takeover reply");
        if (this->ic_status_sensor_ != nullptr)
          this->ic_status_sensor_->publish_state(status);
      }
      
        
        if (!this->tx_queue_.empty() && std::get<0>(this->tx_queue_.front()) == PACKET_TYPE_IC) {
          ESP_LOGD(TAG, "IC Got response, removing from send queue");
          this->tx_queue_.pop();
        }
        
        return true;  // Packet complete
      }
    }
  }
  
  // Check for buffer overflow
  if (len >= 64) {
    ESP_LOGW(TAG, "IntelliChlor packet too long, dropping");
    return true;  // Complete (error)
  }
  
  // Still building packet
  return false;
}

// ========================================
// IntelliFlo Methods
// ========================================

bool PentairIfIcComponent::validate_if_received_message_() {
  uint32_t at = this->rx_buffer_.size() - 1;
  uint8_t *data = &this->rx_buffer_[0];
  
  // Validate IntelliFlo packet header
  if (at == 0) return data[0] == 0xFF;
  if (at == 1) return data[1] == 0x00;
  if (at == 2) return data[2] == 0xFF;
  if (at == 3) return data[3] == 0xA5;
  
  if (at <= 8) return true;
  
  uint8_t packet_size = data[8];
  uint8_t length = (packet_size + 10);
  
  if (at < length) return true;
  
  // Validate checksum
  uint16_t checksum = 0;
  for (int j = 3; j < 3 + packet_size + 6; j++) {
    checksum = checksum + data[j];
  }
  
  uint16_t packet_checksum = (data[3 + 6 + packet_size] << 8) + data[3 + 7 + packet_size];
  if (checksum != packet_checksum) {
    ESP_LOGW(TAG, "IF checksum mismatch, dropping packet");
    return false;
  }
  
  // Remove FF 00 FF header
  rx_buffer_.erase(rx_buffer_.begin());
  rx_buffer_.erase(rx_buffer_.begin());
  rx_buffer_.erase(rx_buffer_.begin());
  
  ESP_LOGV(TAG, "IF Package received: %s", format_hex_pretty(rx_buffer_).c_str());
  ESP_LOGI(TAG, "IF received: %s", describe_if_packet(rx_buffer_).c_str());
  
  parse_if_packet_(rx_buffer_);
  
  return false;  // Reset buffer
}

void PentairIfIcComponent::parse_if_packet_(const std::vector<uint8_t> &data) {
  if (data[3] == 0x60 && data[4] == 0x07) {
    // Pump status packet
    if (this->if_running_ != nullptr) {
      switch (data[6]) {
        case STOPPED:
          this->if_running_->publish_state(false);
          break;
        case RUNNING:
          this->if_running_->publish_state(true);
          break;
        default:
          ESP_LOGW(TAG, "IF received unknown run state");
          break;
      }
    }
    
    if (this->if_program_ != nullptr) {
      switch (data[7]) {
        case NO_PROG:
          this->if_program_->publish_state("");
          break;
        case LOCAL1:
          this->if_program_->publish_state("Local 1");
          break;
        case LOCAL2:
          this->if_program_->publish_state("Local 2");
          break;
        case LOCAL3:
          this->if_program_->publish_state("Local 3");
          break;
        case LOCAL4:
          this->if_program_->publish_state("Local 4");
          break;
        case EXT1:
          this->if_program_->publish_state("External 1");
          break;
        case EXT2:
          this->if_program_->publish_state("External 2");
          break;
        case EXT3:
          this->if_program_->publish_state("External 3");
          break;
        case EXT4:
          this->if_program_->publish_state("External 4");
          break;
        case TIMEOUT:
          this->if_program_->publish_state("Time Out");
          break;
        case PRIMING:
          this->if_program_->publish_state("Priming");
          break;
        case QUICKCLEAN:
          this->if_program_->publish_state("Quick Clean");
          break;
        default:
          ESP_LOGW(TAG, "IF received unknown program");
          break;
      }
    }
    
    if (this->if_power_ != nullptr)
      this->if_power_->publish_state((data[9] * 256) + data[10]);
    if (this->if_rpm_ != nullptr)
      this->if_rpm_->publish_state((data[11] * 256) + data[12]);
    if (this->if_flow_ != nullptr)
      this->if_flow_->publish_state(data[13] * 0.227);
    if (this->if_pressure_ != nullptr)
      this->if_pressure_->publish_state(data[14] / 14.504);
    if (this->if_time_remaining_ != nullptr)
      this->if_time_remaining_->publish_state(data[17] * 60 + data[18]);
    if (this->if_clock_ != nullptr)
      this->if_clock_->publish_state(data[19] * 60 + data[20]);
  }
}

void PentairIfIcComponent::requestPumpStatus() {
  ESP_LOGD(TAG, "IF Requesting pump status");
  uint8_t statusPacket[] = {0xA5, 0x00, 0x60, 0x10, 0x07, 0x00};
  queue_if_packet_(statusPacket, 6);
}

void PentairIfIcComponent::pumpToLocalControl() {
  ESP_LOGD(TAG, "IF Requesting local control");
  uint8_t localControlPacket[] = {0xA5, 0x00, 0x60, 0x10, 0x04, 0x01, 0x00};
  queue_if_packet_(localControlPacket, 7);
}

void PentairIfIcComponent::pumpToRemoteControl() {
  ESP_LOGD(TAG, "IF Requesting remote control");
  uint8_t remoteControlPacket[] = {0xA5, 0x00, 0x60, 0x10, 0x04, 0x01, 0xFF};
  queue_if_packet_(remoteControlPacket, 7);
}

void PentairIfIcComponent::setPumpClock(int hour, int minute) {
  ESP_LOGW(TAG, "IF setting pump clock to %02d:%02d; many IntelliFlo models reject this and the clock must be set on the pump keypad", hour, minute);
  // Not supported on all IntelliFlo models; the pump may reply that the command is not supported.
  uint8_t setClockPacket[] = {0xA5, 0x00, 0x60, 0x10, 0x03, 0x02, 0, 0};
  setClockPacket[6] = hour;
  setClockPacket[7] = minute;
  queue_if_packet_(setClockPacket, 8);
}

void PentairIfIcComponent::run() {
  ESP_LOGD(TAG, "IF Run Pump");
  this->pumpToRemoteControl();
  uint8_t pumpPowerPacket[] = {0xA5, 0x00, 0x60, 0x10, 0x06, 0x01, 0x0A};
  queue_if_packet_(pumpPowerPacket, 7);
}

void PentairIfIcComponent::stop() {
  ESP_LOGD(TAG, "IF Stop Pump");
  this->pumpToRemoteControl();
  uint8_t pumpPowerPacket[] = {0xA5, 0x00, 0x60, 0x10, 0x06, 0x01, 0x04};
  queue_if_packet_(pumpPowerPacket, 7);
}

void PentairIfIcComponent::commandLocalProgram(int prog) {
  ESP_LOGD(TAG, "IF Command local program %d", prog);
  this->pumpToRemoteControl();
  uint8_t pumpPowerPacket[] = {0xA5, 0x00, 0x60, 0x10, 0x05, 0x01, 0};
  pumpPowerPacket[6] = prog + 1;
  queue_if_packet_(pumpPowerPacket, 7);
}

void PentairIfIcComponent::commandExternalProgram(int prog) {
  ESP_LOGD(TAG, "IF Command external program %d", prog);
  this->pumpToRemoteControl();
  uint8_t pumpPowerPacket[] = {0xA5, 0x00, 0x60, 0x10, 0x01, 0x04, 0x03, 0x21, 0x00, 0x00};
  pumpPowerPacket[9] = prog * 8;
  queue_if_packet_(pumpPowerPacket, 10);
}

void PentairIfIcComponent::saveValueForProgram(int prog, int value) {
  ESP_LOGD(TAG, "IF saveValueForProgram %d: %d", prog, value);
  uint8_t pumpPowerPacket[] = {0xA5, 0x00, 0x60, 0x10, 0x01, 0x04, 0x03, 0, 0, 0};
  pumpPowerPacket[7] = 0x26 + prog;
  pumpPowerPacket[8] = floor(value / 256);
  pumpPowerPacket[9] = value % 256;
  queue_if_packet_(pumpPowerPacket, 10);
}

void PentairIfIcComponent::commandRPM(int rpm) {
  ESP_LOGD(TAG, "IF Command RPM: %d rpm", rpm);
  this->pumpToRemoteControl();
  uint8_t pumpPowerPacket[] = {0xA5, 0x00, 0x60, 0x10, 0x01, 0x04, 0x02, 0xC4, 0, 0};
  pumpPowerPacket[8] = floor(rpm / 256);
  pumpPowerPacket[9] = rpm % 256;
  queue_if_packet_(pumpPowerPacket, 10);
}

void PentairIfIcComponent::commandFlow(int flow) {
  ESP_LOGD(TAG, "IF Command Flow: %.1f m3/h", ((double) flow) / 10);
  uint8_t pumpPowerPacket[] = {0xA5, 0x00, 0x60, 0x10, 0x09, 0x04, 0x02, 0xC4, 0x00, 0};
  pumpPowerPacket[9] = flow;
  queue_if_packet_(pumpPowerPacket, 10);
}

void PentairIfIcComponent::queue_if_packet_(uint8_t message[], int messageLength) {
  ESP_LOGV(TAG, "IF queuePacket: message length: %d", messageLength);
  
  int checksum = 0;
  for (int j = 0; j < messageLength; j++) {
    checksum += message[j];
  }
  
  std::vector<uint8_t> packet = {0xFF, 0x00, 0xFF};
  packet.insert(packet.end(), message, message + messageLength);
  packet.push_back(checksum >> 8);
  packet.push_back(checksum & 0xFF);
  
  int packetSize = messageLength + 3 + 2;
  
  // Validate checksum
  int packetchecksum = (packet[packetSize - 2] * 256) + packet[packetSize - 1];
  int databytes = 0;
  for (int i = 3; i < packetSize - 2; i++) {
    databytes += packet[i];
  }
  
  bool validPacket = (packetchecksum == databytes);
  if (!validPacket) {
    ESP_LOGW(TAG, "IF not queueing a malformed pump packet");
  } else {
    this->tx_queue_.push(std::make_tuple(PACKET_TYPE_IF, (uint8_t)0, (uint8_t)0, packet));
  }
}

template<typename... Args>
std::string PentairIfIcComponent::string_format_(const std::string &format, Args... args) {
  int size_s = std::snprintf(nullptr, 0, format.c_str(), args...) + 1;
  if (size_s <= 0) {
    return std::string();
  }
  auto size = static_cast<size_t>(size_s);
  std::unique_ptr<char[]> buf(new char[size]);
  std::snprintf(buf.get(), size, format.c_str(), args...);
  return std::string(buf.get(), buf.get() + size - 1);
}

}  // namespace pentair_if_ic
}  // namespace esphome
