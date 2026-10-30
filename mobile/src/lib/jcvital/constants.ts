// @ts-nocheck — vendored from MoShenGuo/MSDataDemo (MIT), adapted for Telomy (deviceType V8)
import { Platform } from 'react-native';

export default class Constants {
  // UUID 配置
  static NOTIFY = Platform.OS === 'android' 
    ? '00002902-0000-1000-8000-00805f9b34fb' 
    : '00002902-0000-1000-8000-00805f9b34fb';
  static SERVICE_DATA_UUID = 'fff0'
  static SERVICE_DATA = Platform.OS === 'android'
    ? '0000fff0-0000-1000-8000-00805f9b34fb'
    : '0000fff0-0000-1000-8000-00805f9b34fb';
  
  static DATA_CHARACTERISTIC = Platform.OS === 'android'
    ? '0000fff6-0000-1000-8000-00805f9b34fb'
    : '0000fff6-0000-1000-8000-00805f9b34fb';
  
  static NOTIFY_CHARACTERISTIC = Platform.OS === 'android'
    ? '0000fff7-0000-1000-8000-00805f9b34fb'
    : '0000fff7-0000-1000-8000-00805f9b34fb';

  // 蓝牙状态常量
//   static BLUE_METHOD_NAME = 'BLUE_METHOD_NAME';
//   static BLUE_CONNECTING = 'ble_connecting';//连接中
//   static BLUE_CONNECTED = 'ble_connected';//连接成功
//   static BLUE_DISCONNECTED = 'ble_disconnected';//断开连接
  static BLUE_CONNECTION_STATE = 'BLUE_CONNECTION_STATE';
 static BLUE_DATA_RECEIVED = 'BLUE_DATA_RECEIVED';
}


// 自定义事件名
// export const BLE_EVENTS = {
//   CONNECTING: 'ble_connecting',
//   CONNECTED: 'ble_connected',
//   DISCONNECTED: 'ble_disconnected',
//   DATA_RECEIVED: 'ble_data_received',
// };