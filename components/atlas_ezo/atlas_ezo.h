#pragma once

#include "esphome/core/component.h"
#include "esphome/core/hal.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include <string>
#include <vector>

namespace esphome {
namespace atlas_ezo {

// One hardware UART is moved across the three EZO sockets. Each socket
// accepts any Atlas circuit. The silk names are not consulted.
class AtlasEzo : public Component {
 public:
  void add_port(InternalGPIOPin *tx, InternalGPIOPin *rx);
  void set_socket_sensor(uint8_t index, text_sensor::TextSensor *sensor);
  void set_ph_sensor(sensor::Sensor *sensor) { this->ph_ = sensor; }
  void set_orp_sensor(sensor::Sensor *sensor) { this->orp_ = sensor; }
  void set_conductivity_sensor(sensor::Sensor *sensor) { this->conductivity_ = sensor; }
  void set_tds_sensor(sensor::Sensor *sensor) { this->tds_ = sensor; }
  void set_salinity_sensor(sensor::Sensor *sensor) { this->salinity_ = sensor; }
  void set_rtd_sensor(sensor::Sensor *sensor) { this->rtd_ = sensor; }
  void set_do_sensor(sensor::Sensor *sensor) { this->dissolved_oxygen_ = sensor; }

  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return 900.0f; }

 protected:
  enum class Job : uint8_t { INFO, OUTPUTS, READ };

  struct Port {
    InternalGPIOPin *tx{nullptr};
    InternalGPIOPin *rx{nullptr};
    text_sensor::TextSensor *label{nullptr};
    std::string kind;
    std::string shown;
    std::vector<std::string> fields;
    bool uart_mode{true};
    bool identified{false};
    bool outputs_known{false};
    bool have_read{false};
    uint8_t misses{0};
    uint8_t address{0};
    float values[4]{};
    uint8_t nvalues{0};
  };

  void detach_other_pins_(const Port &active);
  void attach_uart_(Port &port);
  void release_uart_();
  void arm_i2c_(Port &port);
  void send_uart_(const char *text, uint32_t wait_ms);
  void pump_uart_();
  bool i2c_probe_(Port &port, uint8_t address);
  void i2c_write_(Port &port, uint8_t address, const char *text);
  std::string i2c_read_(Port &port, uint8_t address);
  void begin_port_();
  void issue_();
  void on_line_(const std::string &line);
  void on_timeout_();
  void advance_();
  void publish_();
  void show_(Port &port, const std::string &text);
  void clear_port_(Port &port);

  bool parse_info_(const std::string &line, std::string &kind);
  bool parse_outputs_(const std::string &line);
  bool parse_reading_(const std::string &line);

  static std::string canon_(const std::string &token);
  static std::string display_(const std::string &kind);

  Port ports_[3];
  uint8_t count_{0};
  uint8_t index_{0};
  uint8_t scan_address_{1};
  Job job_{Job::INFO};
  bool waiting_{false};
  bool line_ready_{false};
  bool disabled_{false};
  bool scanning_{false};
  bool i2c_wait_{false};
  uint32_t deadline_{0};
  uint32_t next_action_{0};
  std::string buffer_;
  bool saw_ph_{false};
  bool saw_orp_{false};
  bool saw_cond_{false};
  bool saw_tds_{false};
  bool saw_sal_{false};
  bool saw_rtd_{false};
  bool saw_do_{false};

  sensor::Sensor *ph_{nullptr};
  sensor::Sensor *orp_{nullptr};
  sensor::Sensor *conductivity_{nullptr};
  sensor::Sensor *tds_{nullptr};
  sensor::Sensor *salinity_{nullptr};
  sensor::Sensor *rtd_{nullptr};
  sensor::Sensor *dissolved_oxygen_{nullptr};
};

}  // namespace atlas_ezo
}  // namespace esphome
