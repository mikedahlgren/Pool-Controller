import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins
from esphome.const import CONF_ID
from esphome.cpp_helpers import gpio_pin_expression

DEPENDENCIES = []
MULTI_CONF = False

CONF_ATLAS_EZO_ID = "atlas_ezo_id"
CONF_PORTS = "ports"
CONF_TX_PIN = "tx_pin"
CONF_RX_PIN = "rx_pin"

atlas_ezo_ns = cg.esphome_ns.namespace("atlas_ezo")
AtlasEzo = atlas_ezo_ns.class_("AtlasEzo", cg.Component)

PORT_SCHEMA = cv.Schema(
    {
        cv.Required(CONF_TX_PIN): pins.internal_gpio_output_pin_schema,
        cv.Required(CONF_RX_PIN): pins.internal_gpio_input_pin_schema,
    }
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
        tx = await gpio_pin_expression(port[CONF_TX_PIN])
        rx = await gpio_pin_expression(port[CONF_RX_PIN])
        cg.add(var.add_port(tx, rx))
