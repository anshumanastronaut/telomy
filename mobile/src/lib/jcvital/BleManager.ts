// @ts-nocheck — vendored from MoShenGuo/MSDataDemo (MIT), adapted for Telomy (deviceType V8)

import { BleSDK } from "@yhmedical/ms-data-sdk";
import { Alert, AppState, PermissionsAndroid, Platform } from 'react-native';
import { BleManager, Characteristic, Device, Service, Subscription } from 'react-native-ble-plx';
import { Base64Utils } from './Base64Utils';
import { SimpleEventEmitter } from './EventBus';
import Constants from './constants';
interface BlueOffData {
  data: number[];
}
class MSBleManager {
  private manager = new BleManager();
  private isScanning = false;
  private _isConnected = false;
  // 当前设备类型 (用于 dataParsingWithData 解析), 可切换: '2208' | 'V4' | 'V5' | '2025' | 'V8' | 'X6'
  public deviceType: any = 'V8';
  private manualDisconnection = false;
  private connectCount = 0;
  private device: Device | null = null;
  private notifySubscription: Subscription | null = null;
  private dataQueue: BlueOffData[] = [];
  private eventEmitter = new SimpleEventEmitter();
  private stateChangeSubscriptions: ((state: string) => void)[] = [];
  private appStateSubscription: any;
  private initialized = false;

  // 单例模式
  private static instance: MSBleManager;
  static getInstance() {
    if (!MSBleManager.instance) {
      MSBleManager.instance = new MSBleManager();
    }
    return MSBleManager.instance;
  }
  // ✅ 核心：提供方法查询真实状态
  public isConnected(): boolean {
    return this._isConnected;
  }
  // 监听事件
  public on(event: string, listener: (...args: any[]) => void) {
    this.eventEmitter.on(event, listener);
  }

  public off(event: string, listener: (...args: any[]) => void) {
    this.eventEmitter.off(event, listener);
  }
  private scannedDevices: Map<string, Device> = new Map();
  // 蓝牙状态监听器
  private bluetoothStateChangeListener?: (state: string) => void;

  // 初始化蓝牙状态监听
  initializeBluetoothStateListener(listener: (state: string) => void) {
    this.bluetoothStateChangeListener = listener;
    this.manager.onStateChange((state) => {
      if (this.bluetoothStateChangeListener) {
        this.bluetoothStateChangeListener(state);
      }
    });
  }
  // 初始化蓝牙（权限 + 蓝牙状态检查）
  async init(): Promise<boolean> {
    if (this.initialized) return await this.checkBluetoothState();

    // Android 权限处理
    if (Platform.OS === 'android') {
      const granted = await this.requestAndroidPermissions();
      if (!granted) {
        Alert.alert('权限不足', '需要位置权限来扫描蓝牙设备');
        return false;
      }
    }

    // iOS 权限检查（虽然 iOS 不需要手动请求权限）
    if (Platform.OS === 'ios') {
      const isBluetoothReady = await this.checkIOSBluetoothState();
      if (!isBluetoothReady) {
        Alert.alert('蓝牙未开启', '请开启蓝牙以使用扫描功能');
        return false;
      }
    }

    // 监听蓝牙状态变化
    this.setupStateChangeListener();

    // App 状态监听（后台/前台切换）
    this.setupAppStateListener();

    this.initialized = true;
    return await this.checkBluetoothState();
  }

  // Android 权限请求
  // 替换原有的 requestAndroidPermissions 方法
private async requestAndroidPermissions(): Promise<boolean> {
  try {
    // 👇 关键：使用 Number() 转成 number 类型
    const version = Number(Platform.Version);

    if (version >= 31) {
      // Android 12+ (API 31+)
      const scanGranted = await PermissionsAndroid.request(
        'android.permission.BLUETOOTH_SCAN',
        {
          title: '蓝牙扫描权限',
          message: '需要蓝牙扫描权限来发现设备',
          buttonNeutral: '稍后',
          buttonNegative: '拒绝',
          buttonPositive: '允许',
        }
      );

      const connectGranted = await PermissionsAndroid.request(
        'android.permission.BLUETOOTH_CONNECT',
        {
          title: '蓝牙连接权限',
          message: '需要蓝牙连接权限来连接设备',
          buttonNeutral: '稍后',
          buttonNegative: '拒绝',
          buttonPositive: '允许',
        }
      );

      const locationGranted = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
        {
          title: '位置权限',
          message: '需要位置权限用于蓝牙扫描（系统要求）',
          buttonNeutral: '稍后',
          buttonNegative: '拒绝',
          buttonPositive: '允许',
        }
      );

      return (
        scanGranted === PermissionsAndroid.RESULTS.GRANTED &&
        connectGranted === PermissionsAndroid.RESULTS.GRANTED &&
        locationGranted === PermissionsAndroid.RESULTS.GRANTED
      );
    } else {
      // Android 6-11
      const granted = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
        {
          title: '位置权限',
          message: '需要位置权限来扫描蓝牙设备',
          buttonNeutral: '稍后',
          buttonNegative: '拒绝',
          buttonPositive: '允许',
        }
      );
      return granted === PermissionsAndroid.RESULTS.GRANTED;
    }
  } catch (err) {
    console.warn('请求权限失败:', err);
    return false;
  }
}

  private async checkIOSBluetoothState(): Promise<boolean> {
  try {
    // 先尝试获取状态
    let state = await this.manager.state();

    if (state === 'PoweredOn') {
      console.log('蓝牙已开启');
      return true;
    }

    // 明确失败状态
    if (state === 'PoweredOff') {
      console.warn('蓝牙已关闭');
      return false;
    }
    if (state === 'Unauthorized') {
      console.warn('蓝牙权限被拒绝');
      return false;
    }
    if (state === 'Unsupported') {
      console.warn('设备不支持蓝牙');
      return false;
    }

    // 如果是 Unknown，进入轮询 + 监听模式
    if (state === 'Unknown') {
      console.log('蓝牙状态未知，等待更新...');

      return new Promise<boolean>((resolve) => {
        let resolved = false;
        const maxAttempts = 10;
        let attempts = 0;

        const interval = setInterval(async () => {
          if (resolved) return;
          attempts++;
          const currentState = await this.manager.state();
          console.log(`[轮询] 蓝牙状态:`, currentState);

          if (currentState === 'PoweredOn') {
            clearInterval(interval);
            stateListener?.remove();
            resolved = true;
            resolve(true);
          } else if (['PoweredOff', 'Unauthorized', 'Unsupported'].includes(currentState)) {
            clearInterval(interval);
            stateListener?.remove();
            resolved = true;
            resolve(false);
          } else if (attempts >= maxAttempts) {
            clearInterval(interval);
            stateListener?.remove();
            resolved = true;
            console.warn('蓝牙状态检查超时');
            resolve(false);
          }
        }, 500);

        // 同时监听状态变化
        const stateListener = this.manager.onStateChange((newState) => {
          console.log('onStateChange:', newState);
          if (resolved) return;

          if (newState === 'PoweredOn') {
            clearInterval(interval);
            stateListener.remove();
            resolved = true;
            resolve(true);
          } else if (['PoweredOff', 'Unauthorized', 'Unsupported'].includes(newState)) {
            clearInterval(interval);
            stateListener.remove();
            resolved = true;
            resolve(false);
          }
          // 注意：这里不要对 'Unknown' 做 resolve，继续等待
        }, true); // true 表示立即触发一次当前状态
      });
    }

    return false;
  } catch (error) {
    console.error('检查蓝牙状态失败:', error);
    return false;
  }
}

  // 监听蓝牙状态变化
  onStateChange(callback: (state: string) => void): Subscription {
    this.stateChangeSubscriptions.push(callback);
    return {
      remove: () => {
        this.stateChangeSubscriptions = this.stateChangeSubscriptions.filter(cb => cb !== callback);
      },
    };
  }

  // 内部触发蓝牙状态变更
  private setupStateChangeListener() {
    this.manager.onStateChange((state) => {
      this.stateChangeSubscriptions.forEach(cb => cb(state));
    }, true);
  }

  // App 状态监听（前后台切换）
  private setupAppStateListener() {
    this.appStateSubscription = AppState.addEventListener('change', async (nextAppState) => {
      if (nextAppState === 'active') {
        // App 回到前台，重新检查蓝牙状态
        const state = await this.manager.state();
        this.stateChangeSubscriptions.forEach(cb => cb(state));
      }
    });
  }
  // 检查并请求蓝牙权限（仅限Android）
  async requestBluetoothPermissions(): Promise<boolean> {
    if (Platform.OS === 'android') {
      try {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
          {
            title: '位置权限',
            message: '需要位置权限来扫描蓝牙设备',
            buttonNeutral: '稍后',
            buttonNegative: '拒绝',
            buttonPositive: '允许',
          }
        );
        return granted === PermissionsAndroid.RESULTS.GRANTED;
      } catch (err) {
        console.warn(err);
        return false;
      }
    }
    // iOS 不需要请求权限，但需要在 Info.plist 中配置
    return true;
  }

  // 检查蓝牙状态是否准备好
  async checkBluetoothState(): Promise<boolean> {
    const state = await this.manager.state();
    if (state !== 'PoweredOn') {
      console.error('蓝牙未开启或不可用:', state);
      return false;
    }
    return true;
  }
  async startScan(onDeviceFound: (device: Device) => void) {
    if (this.isScanning) return;
    const isBluetoothReady = await this.waitForBluetoothPoweredOn();
    if (!isBluetoothReady) {
      console.warn('蓝牙未准备好，无法连接设备');
      return;
    }

    // 🔥 再次确保权限（尤其 Android 12+）
    const hasPermission = await this.checkAndroidPermissions();
    if (!hasPermission) {
      Alert.alert('权限不足', '请在设置中开启蓝牙和位置权限');
      return;
    }
    this.isScanning = true;
    this.manager.startDeviceScan(null, null, (error, device) => {
      if (error) {
        console.error('扫描错误:', error);
        this.stopScan();
        return;
      }

      if (device?.id) {
        this.scannedDevices.set(device.id, device);
        onDeviceFound(device);
      }
    });
  }
  private async checkAndroidPermissions(): Promise<boolean> {
    if (Platform.OS !== 'android') return true;

    const version = Platform.Version;

    if (version >= 31) {
      const scan = await PermissionsAndroid.check('android.permission.BLUETOOTH_SCAN');
      const connect = await PermissionsAndroid.check('android.permission.BLUETOOTH_CONNECT');
      const location = await PermissionsAndroid.check(PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION);
      return scan && connect && location;
    } else {
      const location = await PermissionsAndroid.check(PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION);
      return location;
    }
  }
  async getDeviceById(deviceId: string): Promise<Device | null> {
    const devi = this.scannedDevices.get(deviceId);
    if (devi) {
      return devi;
    } else {
      try {
        const devices = await this.manager.devices([deviceId]);
        return devices.length > 0 ? devices[0] : null;
      } catch (error) {
        console.error('查找设备失败:', error);
        return null;
      }
    }
  }
  stopScan() {
    this.isScanning = false;
    this.manager.stopDeviceScan();
  }

  async connectDeviceById(deviceId: string) {
    if (!deviceId) {
      console.error('设备 ID 为空，无法连接');
      return;
    }

    const isBluetoothReady = await this.waitForBluetoothPoweredOn();
    if (!isBluetoothReady) {
      console.warn('蓝牙未准备好，无法连接设备');
      return;
    }

    try {
      const device = await this.getDeviceById(deviceId);
      if (!device) {
        console.warn('设备不在缓存中，尝试重新发现');
        throw new Error('设备未找到');
        // const freshDevice = await this.manager.findDeviceById(deviceId);
        // if (!freshDevice) throw new Error('设备未找到');
        // return this.connectDevice(freshDevice);
      } else {
        this.connectDevice(device);
      }
    } catch (error) {
      console.error('连接失败:', error);
      this.handleDisconnection();
    } finally {
      this.dismissDialog();
    }
  }
  /**
   * 等待蓝牙状态变为 PoweredOn，最多等待 3 秒
   * @returns Promise<boolean> 是否成功等到蓝牙开启
   */
  async waitForBluetoothPoweredOn(): Promise<boolean> {
    return new Promise((resolve) => {
      const timeout = 3000; // 3秒超时
      let resolved = false;

      const checkState = async () => {
        const state = await this.manager.state();
        if (state === 'PoweredOn') {
          if (!resolved) {
            resolved = true;
            resolve(true);
          }
          return;
        } else if (state === 'Unsupported' || state === 'Unauthorized') {
          if (!resolved) {
            resolved = true;
            resolve(false);
          }
          return;
        }

        // 如果还没准备好，继续监听
        const subscription = this.manager.onStateChange((newState) => {
          if (newState === 'PoweredOn') {
            if (!resolved) {
              resolved = true;
              resolve(true);
            }
            subscription.remove();
          } else if (newState === 'Unsupported' || newState === 'Unauthorized') {
            if (!resolved) {
              resolved = true;
              resolve(false);
            }
            subscription.remove();
          }
        });
      };

      checkState();

      // 设置超时
      setTimeout(() => {
        if (!resolved) {
          resolved = true;
          resolve(false);
        }
      }, timeout);
    });
  }
  // 连接设备
  async connectDevice(device: Device | null | undefined) {
    if (!device) {
      console.error('无法连接：device 为 undefined 或 null');
      return;
    }
    this.showLoadDialog('连接中');

    try {
      this.device = await device.connect();
      this.setupListeners();

      const connectedDevice = await this.device.discoverAllServicesAndCharacteristics();
      this.handleServiceDiscovery(connectedDevice);

      this._isConnected = true;
      this.manualDisconnection = false;
      this.eventEmitter.emit(Constants.BLUE_CONNECTION_STATE, true);
    } catch (error) {
      console.error('Connection failed:', error);
      this.eventEmitter.emit(Constants.BLUE_CONNECTION_STATE, false);
      this.handleDisconnection();
    } finally {
      this.dismissDialog();
    }
  }
  private handleDisconnection() {
    try {
      this._isConnected = false;
      this.device?.cancelConnection();
    } catch (error) {
      console.error('cancelConnection failed:', error);
    } finally {

    }

  }

  private setupListeners() {
    if (!this.device) return;

    // 设备断开监听
    this.device.onDisconnected((error, device) => {
      this._isConnected = false;
      this.eventEmitter.emit(Constants.BLUE_CONNECTION_STATE, false);

      if (!this.manualDisconnection && this.connectCount < 2) {
        this.connectCount++;
        setTimeout(() => this.connectDevice(device), 1000);
      } else {
        this.connectCount = 0;
        this.manualDisconnection = true;
        this.cleanup();
      }
    });
  }

  private async handleServiceDiscovery(device: Device) {
    const services = await device.services();

    for (const service of services) {
      console.log('service:', service.uuid);
      if (service.uuid.toLowerCase() === Constants.SERVICE_DATA.toLowerCase()) {
        const characteristics = await service.characteristics();
        this.setupNotifyCharacteristic(characteristics, service);
      }
    }
  }

  private setupNotifyCharacteristic(characteristics: Characteristic[], service: Service) {
    const notifyChar = characteristics.find(c =>
      c.uuid.toLowerCase() === Constants.NOTIFY_CHARACTERISTIC.toLowerCase()
    );
    console.log('setupNotifyCharacteristic');
    if (notifyChar) {
      this.notifySubscription = notifyChar.monitor((error, characteristic) => {
        if (error || !characteristic?.value) {
          console.log('notifysu:', error);
          return;
        }
        // 使用封装的方法统一解析数据
        const valueArray = Base64Utils.parseCharacteristicValue(characteristic.value);
        const data = BleSDK.dataParsingWithData(valueArray, this.deviceType);
        console.log('Receive:', data);
        this.eventEmitter.emit(Constants.BLUE_DATA_RECEIVED, data);
        this.eventEmitter.emit('dataByteCallBack', valueArray);
      });
    }
  }

  // 数据写入
  writeData(data: number[]) {
    if (!this.device || !this._isConnected) {
      this.showContentDialog('设备未连接');
      return;
    }


    // const buffer = Buffer.from(data);
    const base64String = Base64Utils.toBase64(data);
    this.device.writeCharacteristicWithResponseForService(
      Constants.SERVICE_DATA,
      Constants.DATA_CHARACTERISTIC,
      base64String
    ).then(() => {
      this.processNextInQueue();
    });
  }

  // 长数据队列处理
  offerData(data: number[]) {
    this.dataQueue.push({ data });
    if (this.dataQueue.length === 1) {
      this.processNextInQueue();
    }
  }

  private processNextInQueue() {
    if (this.dataQueue.length === 0) return;

    const { data } = this.dataQueue.shift()!;
    this.writeData(data);
  }

  // 断开连接
  disconnectDevice() {
    this.manualDisconnection = true;
    if (this.device) {
      this.device.cancelConnection();
    }
    this.cleanup();
  }

  private cleanup() {
    this.notifySubscription?.remove();
    this.notifySubscription = null;
    this.device = null;
    this.dataQueue = [];
  }

  // UI 相关方法 (需根据实际UI库实现)
  private showLoadDialog(text: string) {
    // 使用您的UI库显示加载框
  }

  private dismissDialog() {
    // 关闭对话框
  }

  private showContentDialog(text: string) {
    // 显示内容对话框
  }
  // 销毁资源
  destroy() {
    this.stopScan();
    this.manager.destroy();
    if (this.appStateSubscription) {
      this.appStateSubscription.remove();
    }
  }
}
// export default MSBleManager.getInstance();
export const bleManager = MSBleManager.getInstance();


// import { Buffer } from "buffer";
// import { EventEmitter } from "eventemitter3";
// import { BleManager, Device } from "react-native-ble-plx";
// import Constants from "./constants";
// // import Constants from "constants";

// class MSBleManager extends EventEmitter {
//   private bleManager: BleManager;
//   private connectedDevice: Device | null = null;

//   constructor() {
//     super();
//     this.bleManager = new BleManager();
//   }

//   isConnected(): boolean {
//     return this.connectedDevice != null;
//   }

//   async connectDeviceById(deviceId: string) {
//     try {
//       console.log("开始连接设备:", deviceId);
//       const device = await this.bleManager.connectToDevice(deviceId);
//       this.connectedDevice = device;

//       await device.discoverAllServicesAndCharacteristics();
//       console.log("服务和特征已发现");

//       // 🔑 订阅特征
//       const SERVICE_UUID = Constants.SERVICE_DATA;        // TODO: 替换
//       const CHARACTERISTIC_UUID =  Constants.NOTIFY_CHARACTERISTIC; // TODO: 替换

//       device.monitorCharacteristicForService(
//         SERVICE_UUID,
//         CHARACTERISTIC_UUID,
//         (error, characteristic) => {
//           if (error) {
//             console.error("订阅出错:", error);
//             return;
//           }

//           if (characteristic?.value) {
//             const raw = Buffer.from(characteristic.value, "base64");
//             const bytes = Array.from(raw);

//             // 分发原始数据
//             this.emit("dataByteCallBack", bytes);

//             // 解析后的数据
//             this.emit(Constants.BLUE_DATA_RECEIVED, {
//               cmd: bytes[0],
//               payload: bytes.slice(1),
//             });
//           }
//         }
//       );

//       this.emit(Constants.BLUE_CONNECTION_STATE, true);
//     } catch (error) {
//       console.error("连接失败:", error);
//       this.emit(Constants.BLUE_CONNECTION_STATE, false);
//     }
//   }

//   async disconnectDevice() {
//     if (this.connectedDevice) {
//       await this.bleManager.cancelDeviceConnection(this.connectedDevice.id);
//       this.connectedDevice = null;
//       this.emit(Constants.BLUE_CONNECTION_STATE, false);
//     }
//   }

//   async writeData(data: number[]) {
//     if (!this.connectedDevice) {
//       console.warn("没有已连接设备，无法写入");
//       return;
//     }


//     const base64Data = Buffer.from(data).toString("base64");
//     await this.connectedDevice.writeCharacteristicWithResponseForService(
//       Constants.SERVICE_DATA,
//       Constants.DATA_CHARACTERISTIC,
//       base64Data
//     );
//   }
// }

// export const bleManager = new MSBleManager();
