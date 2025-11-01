# ExpressLRS CRSF Protocol Receiver

Raspberry PiのGPIO14（TXD）とGPIO15（RXD）を使用して、ExpressLRS受信機からCRSF（Crossfire）プロトコルのデータを読み取るプログラム

## 概要

このプログラムは、ExpressLRS受信機から送信されるCRSFプロトコルのフレームを解析し、RCチャンネルデータとリンク統計情報を取得します。

### 対応データ

- **RCチャンネル**: 16チャンネル（11ビット分解能、172-1811の範囲）
- **リンク統計**: RSSI、リンク品質、SNR、アンテナ情報、RF Mode、送信電力

## GPIO ピン配置

```
Raspberry Pi              ExpressLRS Receiver
GPIO14 (TXD, Pin 8)  -->  RX
GPIO15 (RXD, Pin 10) <--  TX
GND (Pin 6)          ---  GND
5V (Pin 2/4)         ---  5V (受信機による)
```

## CRSFプロトコルについて

- **ボーレート**: 420000 bps（標準）
- **フレーム形式**: [Address][Length][Type][Payload...][CRC8]
- **CRC**: DVB-S2方式のCRC8
- **チャンネル解像度**: 11ビット（0-2047）
- **更新レート**: 約50-150Hz（ExpressLRSの設定による）

## 必要な設定

### 1. シリアルポートの有効化

```bash
sudo raspi-config
```

- `3 Interface Options` → `I6 Serial Port` を選択
- "Would you like a login shell to be accessible over serial?" → **No**
- "Would you like the serial port hardware to be enabled?" → **Yes**
- 再起動

### 2. Bluetoothの無効化（必須）

Raspberry Pi 3以降では、420kbpsの高速通信のためBluetoothを無効化する必要があります：

```bash
sudo nano /boot/firmware/config.txt
```

以下の行を追加：
```
dtoverlay=disable-bt
```

保存して再起動後、以下のコマンドを実行（いらないかも）：
```bash
sudo systemctl disable hciuart
```

### 3. Python仮想環境の作成とパッケージのインストール

プロジェクトごとに独立したPython環境を作成することを推奨します。

```bash
# 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
source venv/bin/activate

# パッケージのインストール
pip3 install -r requirements.txt
```

**注意**: プログラムを実行する際は、毎回仮想環境を有効化する必要があります：
```bash
source venv/bin/activate
python3 crsf_receiver.py
```

仮想環境を無効化する場合：
```bash
deactivate
```

### 4. ユーザー権限の設定

```bash
sudo usermod -a -G dialout $USER
```

ログアウトして再ログイン、または再起動してください。

## 使用方法

### スクリプト使用前に ExpressLRS 送信機と受信機をバインドしておく
bind 方法については以下の URL を参照してください。

[BetaFPV Nano TX V2 モジュール](https://manuals.plus/ja/betafpv/2at6x-nano-tx-v2-module-manual)
[BetaFPV Nano Receiver](https://support.betafpv.com/hc/en-us/article_attachments/4403870819737)

### 基本的な使い方

```bash
# デフォルトポートで実行
python3 crsf_receiver.py

# カスタムポートを指定
python3 crsf_receiver.py /dev/ttyAMA0
```

### 実行可能にする

```bash
chmod +x crsf_receiver.py
./crsf_receiver.py
```

# テストの実行
python3 test_crsf.py

## 出力例

プログラムを実行すると、リアルタイムでチャンネル値とリンク統計が表示されます：

```
ExpressLRS CRSF Protocol Receiver
GPIO14 (TXD) and GPIO15 (RXD)
--------------------------------------------------------------------------------
CRSF receiver opened on /dev/serial0
Baudrate: 420000 bps

================================================================================
CRSF Monitor Mode
Press Ctrl+C to stop
================================================================================

================================================================================
RC Channels (11-bit / microseconds):
--------------------------------------------------------------------------------
Ch 1:  992 (1500µs)  Ch 2:  992 (1500µs)  Ch 3:  172 (1000µs)  Ch 4:  992 (1500µs)  
Ch 5:  992 (1500µs)  Ch 6:  992 (1500µs)  Ch 7:  992 (1500µs)  Ch 8:  992 (1500µs)  
Ch 9:  992 (1500µs)  Ch10:  992 (1500µs)  Ch11:  992 (1500µs)  Ch12:  992 (1500µs)  
Ch13:  992 (1500µs)  Ch14:  992 (1500µs)  Ch15:  992 (1500µs)  Ch16:  992 (1500µs)  

================================================================================
Link Statistics:
--------------------------------------------------------------------------------
RSSI 1:        -67 dBm
RSSI 2:        -70 dBm
Link Quality:  100 %
SNR:            10 dB
Active Ant:    0
RF Mode:       4
TX Power:      10

Frames: 1250, Errors: 2, Error Rate: 0.16%
```

## プログラム構造

### CRSFReceiverクラス

ExpressLRS受信機からのCRSFデータを処理するメインクラスです。

#### 主要なメソッド

- `open()` - シリアルポートを開く
- `close()` - シリアルポートを閉じる
- `read_frame()` - CRSFフレームを読み取り・解析
- `get_channels()` - RCチャンネル値を取得（11ビット生値）
- `get_channels_normalized()` - 正規化されたチャンネル値を取得（-1.0～1.0）
- `get_channels_microseconds()` - チャンネル値をマイクロ秒で取得（1000-2000µs）
- `get_link_statistics()` - リンク統計情報を取得
- `get_statistics()` - フレーム統計（受信数、エラー数）を取得

### チャンネル値の形式

CRSFチャンネルは3つの形式で取得できます：

1. **11ビット生値** (172-1811)
   ```python
   channels = crsf.get_channels()  # [992, 992, 172, ...]
   ```

2. **正規化値** (-1.0～1.0)
   ```python
   channels_norm = crsf.get_channels_normalized()  # [0.0, 0.0, -1.0, ...]
   ```

3. **マイクロ秒** (1000-2000µs)
   ```python
   channels_us = crsf.get_channels_microseconds()  # [1500, 1500, 1000, ...]
   ```

## カスタムプログラムでの使用例

```python
#!/usr/bin/env python3
from crsf_receiver import CRSFReceiver
import time

# CRSFレシーバーを初期化
crsf = CRSFReceiver(port='/dev/serial0')

if crsf.open():
    print("CRSF Receiver started")
    
    try:
        while True:
            # フレームを読み取る
            if crsf.read_frame():
                # チャンネル値を取得（マイクロ秒）
                channels = crsf.get_channels_microseconds()
                
                # スロットル（チャンネル3）をチェック
                throttle = channels[2]
                if throttle > 1500:
                    print(f"Throttle up: {throttle}µs")
                
                # リンク品質をチェック
                stats = crsf.get_link_statistics()
                if stats['link_quality'] < 50:
                    print(f"Warning: Low link quality {stats['link_quality']}%")
            
            time.sleep(0.01)  # 100Hz
    
    except KeyboardInterrupt:
        print("\nStopped")
    
    finally:
        crsf.close()
```

## ドローン制御への応用例

```python
#!/usr/bin/env python3
from crsf_receiver import CRSFReceiver
import time

def map_channel_to_servo(channel_us, min_us=1000, max_us=2000):
    """
    チャンネル値をサーボ角度にマッピング
    """
    # 1000-2000µs を 0-180度にマッピング
    angle = (channel_us - min_us) * 180 / (max_us - min_us)
    return max(0, min(180, angle))

def control_drone():
    crsf = CRSFReceiver()
    
    if not crsf.open():
        return
    
    print("Drone controller started")
    print("Channel mapping:")
    print("  Ch1: Roll")
    print("  Ch2: Pitch")
    print("  Ch3: Throttle")
    print("  Ch4: Yaw")
    
    try:
        while True:
            if crsf.read_frame():
                channels = crsf.get_channels_microseconds()
                
                # スティック入力を取得
                roll = channels[0]
                pitch = channels[1]
                throttle = channels[2]
                yaw = channels[3]
                
                # Armスイッチ（Ch5）をチェック
                arm_switch = channels[4]
                armed = arm_switch > 1500
                
                if armed and throttle > 1100:
                    print(f"Armed - R:{roll} P:{pitch} T:{throttle} Y:{yaw}")
                    # ここでモーター制御を追加
                else:
                    print("Disarmed")
                
                # リンク品質の監視
                stats = crsf.get_link_statistics()
                if stats['link_quality'] < 30:
                    print("CRITICAL: Failsafe - Low link quality!")
            
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\nShutdown")
    finally:
        crsf.close()

if __name__ == "__main__":
    control_drone()
```

## トラブルシューティング

### データが受信できない

1. **シリアルポートが開けない**
   ```bash
   # ポートの確認
   ls -l /dev/serial* /dev/ttyAMA* /dev/ttyS*
   
   # 権限の確認
   groups  # dialout が含まれているか確認
   ```

2. **ボーレートの確認**
   - CRSFは420000 bpsが標準です
   - 一部のExpressLRS設定では異なる場合があります

3. **配線の確認**
   - TX ↔ RX が正しくクロス接続されているか
   - GNDが共通接続されているか
   - 電源電圧が適切か（3.3Vまたは5V）

4. **Bluetoothの確認**
   ```bash
   # Bluetoothが無効化されているか確認
   cat /boot/config.txt | grep -E "dtoverlay=disable-bt|enable_uart"
   
   # hciuartサービスが停止しているか確認
   systemctl status hciuart
   ```

### フレームエラーが多い

1. **CRC エラー**
   - ノイズが多い環境の可能性
   - 配線を短くする、シールドケーブルを使用
   - GND接続を確認

2. **フレームロス**
   - 受信機の電源電圧が不安定
   - アンテナの向きや距離を確認
   - 送信機のパワーを確認

### リンク統計が表示されない

ExpressLRSの設定で、Link Statistics の送信が有効になっているか確認してください。通常、デフォルトで有効です。

## ExpressLRS設定

### 推奨設定

ExpressLRSコンフィギュレーターで以下を確認：

- **Serial Protocol**: CRSF
- **Serial Baud**: 420000
- **Telemetry**: Enabled（リンク統計用）

### パフォーマンス

- **更新レート**: ExpressLRSの設定により50Hz～500Hz
  - 50Hz: 長距離モード
  - 150Hz: バランス
  - 500Hz: 低遅延モード

## チャンネルマッピング例

標準的なチャンネルマッピング（Mode 2）：

| チャンネル | 機能 | 用途 |
|----------|------|------|
| Ch1 | Roll (Aileron) | 左右傾き |
| Ch2 | Pitch (Elevator) | 前後傾き |
| Ch3 | Throttle | スロットル |
| Ch4 | Yaw (Rudder) | 回転 |
| Ch5 | Arm Switch | モーター始動 |
| Ch6 | Flight Mode | 飛行モード切替 |
| Ch7-16 | AUX | 補助チャンネル |

## 参考資料

- [ExpressLRS Documentation](https://www.expresslrs.org/)
- [CRSF Protocol Specification](https://github.com/crsf-wg/crsf/wiki)
- [TBS Crossfire Protocol](https://www.team-blacksheep.com/products/prod:crossfire)
- [Raspberry Pi UART Configuration](https://www.raspberrypi.com/documentation/computers/configuration.html#configuring-uarts)

## ライセンス

MIT License
