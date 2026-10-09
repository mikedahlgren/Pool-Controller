import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor
from esphome.const import DEVICE_CLASS_PH, DEVICE_CLASS_TEMPERATURE

from . import CONF_ATLAS_EZO_ID, AtlasEzo

DEPENDENCIES = ["atlas_ezo"]

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_ATLAS_EZO_ID): cv.use_id(AtlasEzo),
        cv.Optional("ph"): sensor.sensor_schema(
            unit_of_measurement="pH",
            accuracy_decimals=2,
            device_class=DEVICE_CLASS_PH,
        ),
        cv.Optional("orp"): sensor.sensor_schema(
            unit_of_measurement="mV",
            accuracy_decimals=0,
        ),
        cv.Optional("conductivity"): sensor.sensor_schema(
            unit_of_measurement="µS/cm",
            accuracy_decimals=0,
        ),
        cv.Optional("tds"): sensor.sensor_schema(
            unit_of_measurement="ppm",
            accuracy_decimals=0,
        ),
        cv.Optional("salinity"): sensor.sensor_schema(
            unit_of_measurement="PSU",
            accuracy_decimals=2,
        ),
        cv.Optional("rtd"): sensor.sensor_schema(
            unit_of_measurement="°F",
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_TEMPERATURE,
        ),
        cv.Optional("dissolved_oxygen"): sensor.sensor_schema(
            unit_of_measurement="mg/L",
            accuracy_decimals=2,
        ),
    }
)


async def to_code(config):
    var = await cg.get_variable(config[CONF_ATLAS_EZO_ID])
    for key, setter in (
        ("ph", "set_ph_sensor"),
        ("orp", "set_orp_sensor"),
        ("conductivity", "set_conductivity_sensor"),
        ("tds", "set_tds_sensor"),
        ("salinity", "set_salinity_sensor"),
        ("rtd", "set_rtd_sensor"),
        ("dissolved_oxygen", "set_do_sensor"),
    ):
        if conf := config.get(key):
            sens = await sensor.new_sensor(conf)
            cg.add(getattr(var, setter)(sens))
