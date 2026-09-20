#pragma once

// ANSI colors for the log *body*. ESPHome still paints [I]/[D]/[W] by level.
// Device logs in ESPHome Builder / HA pass these through when ANSI is enabled.
//
//   yellow  — ESP → IntelliFlo (commands)
//   cyan    — IntelliFlo → ESP (replies)
//   blue    — air / water temperature
//   magenta — filter pressure
//   green   — pH / acid
//   white   — schedule, mode, lights

#define POOL_LOG_TX "\033[1;33m"
#define POOL_LOG_RX "\033[1;36m"
#define POOL_LOG_TEMP "\033[1;34m"
#define POOL_LOG_FILTER "\033[1;35m"
#define POOL_LOG_PH "\033[1;32m"
#define POOL_LOG_SCHED "\033[1;37m"
#define POOL_LOG_LIGHT "\033[1;37m"
#define POOL_LOG_END "\033[0m"
