/**
 * Filter tank head-pressure API
 * Yosoo 4-20mA (or equivalent) transmitter on GPIO4
 */

import { BaseESPHomeClient } from './base.js';
import { BinarySensorState, SensorState, NumberState } from '../types.js';

export interface FilterPressureReadings {
  pressurePsi: number;
  pressureBar: number;
  loopCurrentMa: number;
  voltage: number;
  cleanPsi: number;
  risePsi: number;
  needsBackwash: boolean;
  fault: boolean;
}

export class FilterPressureAPI extends BaseESPHomeClient {
  async getStatus(): Promise<FilterPressureReadings> {
    const [psi, bar, ma, volts, clean, rise, backwash, fault] = await Promise.all([
      this.request<SensorState>('/sensor/filter_tank_pressure'),
      this.request<SensorState>('/sensor/filter_tank_pressure_bar'),
      this.request<SensorState>('/sensor/filter_loop_current'),
      this.request<SensorState>('/sensor/filter_pressure_voltage'),
      this.request<NumberState>('/number/filter_clean_pressure'),
      this.request<NumberState>('/number/filter_pressure_rise'),
      this.request<BinarySensorState>('/binary_sensor/filter_needs_backwash'),
      this.request<BinarySensorState>('/binary_sensor/filter_pressure_fault'),
    ]);

    return {
      pressurePsi: psi.value,
      pressureBar: bar.value,
      loopCurrentMa: ma.value,
      voltage: volts.value,
      cleanPsi: clean.value,
      risePsi: rise.value,
      needsBackwash: backwash.value,
      fault: fault.value,
    };
  }

  async getPressurePsi(): Promise<number> {
    const response = await this.request<SensorState>('/sensor/filter_tank_pressure');
    return response.value;
  }

  async saveCleanPressure(): Promise<void> {
    await this.request('/button/save_clean_filter_pressure/press', 'POST');
  }
}
