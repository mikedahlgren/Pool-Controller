import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import text_sensor

from . import CONF_ATLAS_EZO_ID, AtlasEzo

DEPENDENCIES = ["atlas_ezo"]

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_ATLAS_EZO_ID): cv.use_id(AtlasEzo),
        cv.Optional("socket_1"): text_sensor.text_sensor_schema(),
        cv.Optional("socket_2"): text_sensor.text_sensor_schema(),
        cv.Optional("socket_3"): text_sensor.text_sensor_schema(),
    }
)


async def to_code(config):
    var = await cg.get_variable(config[CONF_ATLAS_EZO_ID])
    for index, key in enumerate(("socket_1", "socket_2", "socket_3")):
        if conf := config.get(key):
            sens = await text_sensor.new_text_sensor(conf)
            cg.add(var.set_socket_sensor(index, sens))
