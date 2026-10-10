import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins
from esphome.components import i2c
from esphome.const import CONF_ID
from esphome.cpp_helpers import gpio_pin_expression

DEPENDENCIES = []
MULTI_CONF = False

CONF_ATLAS_EZO_ID = "atlas_ezo_id"
CONF_PORTS = "ports"
CONF_TX_PIN = "tx_pin"
CONF_RX_PIN = "rx_pin"
CONF_I2C_ID = "i2c_id"

atlas_ezo_ns = cg.esphome_ns.namespace("atlas_ezo")
AtlasEzo = atlas_ezo_ns.class_("AtlasEzo", cg.Component)

def _port_schema(value):
    if CONF_I2C_ID in value:
        if CONF_TX_PIN in value or CONF_RX_PIN in value:
            raise cv.Invalid("An I2C port does not take tx_pin or rx_pin")
        return value
    if CONF_TX_PIN not in value or CONF_RX_PIN not in value:
        raise cv.Invalid("A UART port needs tx_pin and rx_pin")
    return value


PORT_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.Optional(CONF_TX_PIN): pins.internal_gpio_output_pin_schema,
            cv.Optional(CONF_RX_PIN): pins.internal_gpio_input_pin_schema,
            cv.Optional(CONF_I2C_ID): cv.use_id(i2c.I2CBus),
        }
    ),
    _port_schema,
)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(AtlasEzo),
        cv.Required(CONF_PORTS): cv.All(
            cv.ensure_list(PORT_SCHEMA), cv.Length(min=1, max=3)
        ),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    for port in config[CONF_PORTS]:
        if CONF_I2C_ID in port:
            bus = await cg.get_variable(port[CONF_I2C_ID])
            cg.add(var.add_i2c_port(bus))
            continue
        tx = await gpio_pin_expression(port[CONF_TX_PIN])
        rx = await gpio_pin_expression(port[CONF_RX_PIN])
        cg.add(var.add_port(tx, rx))
