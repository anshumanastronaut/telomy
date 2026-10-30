// @ts-nocheck — vendored from MoShenGuo/MSDataDemo (MIT), adapted for Telomy (deviceType V8)
// utils/Base64Utils.ts


/**
 * Base64 工具类，用于将 number[] 转换为 Base64 字符串
 */
export class Base64Utils {
  private static readonly base64Chars =
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
    'abcdefghijklmnopqrstuvwxyz' +
    '0123456789+/';

  /**
   * 将 number[] 字节数组转换为 Base64 字符串
   * @param bytes 字节数组，例如 [0x01, 0x02, 0x03]
   * @returns Base64 编码字符串
   */
  public static toBase64(bytes: number[]): string {
    let i = 0;
    let base64 = '';

    while (i < bytes.length) {
      const byte1 = bytes[i++] ?? 0;
      const byte2 = bytes[i++] ?? 0;
      const byte3 = bytes[i++] ?? 0;

      const triplet = (byte1 << 16) | (byte2 << 8) | byte3;

      base64 += this.base64Chars[(triplet >> 18) & 0x3f];
      base64 += this.base64Chars[(triplet >> 12) & 0x3f];
      base64 += this.base64Chars[(triplet >> 6) & 0x3f];
      base64 += this.base64Chars[triplet & 0x3f];
    }

    const pad = bytes.length % 3;
    if (pad === 1) {
      base64 = base64.slice(0, -2) + '==';
    } else if (pad === 2) {
      base64 = base64.slice(0, -1) + '=';
    }

    return base64;
  }
/**
 * 将 characteristic.value 解析为 number[]
 * @param value characteristic.value（iOS 是 Base64 字符串，Android 是 ArrayBuffer）
 * @returns number[] 字节数组
 */
public static  parseCharacteristicValue(value: any): number[] {
  let buffer: Uint8Array;

  if (typeof value === 'string') {
    // 无论是 iOS 还是 Android，只要 value 是字符串，就按 Base64 解析
    buffer = this.base64ToArrayBuffer(value);
  } else if (value instanceof ArrayBuffer) {
    // Android 正常情况：ArrayBuffer
    buffer = new Uint8Array(value);
  } else if (ArrayBuffer.isView(value)) {
    // 兼容 TypedArray（如 Int8Array 等）
    buffer = new Uint8Array(value.buffer);
  } else {
    console.warn('Unknown characteristic.value type:', typeof value, value);
    return [];
  }
  return Array.from(buffer);
}
  private static base64ToArrayBuffer(base64: string): Uint8Array {
  const binaryString = atob(base64);
  const length = binaryString.length;
  const buffer = new Uint8Array(length);

  for (let i = 0; i < length; i++) {
    buffer[i] = binaryString.charCodeAt(i);
  }

  return buffer;
}
}