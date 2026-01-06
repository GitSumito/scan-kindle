
# 必要なライブラリのインポート
import sys, os

# プロジェクトルートにライブラリ（objc, Quartz等）が直接配置されているため、
# それらを読み込まないように sys.path からスクリプトのディレクトリを除外する
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir in sys.path:
    sys.path.remove(script_dir)

# 仮想環境のパスを明示的に追加
venv_site = os.path.join(script_dir, '.venv', 'lib', 'python3.13', 'site-packages')
if os.path.isdir(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)

import pyautogui as pag
import os.path as osp
import datetime, time
import cv2
import numpy as np

# macOS specific imports
try:
    import Quartz
    import AppKit
    # CoreGraphics is part of Quartz in partial imports or not needed if using Quartz namespace
except ImportError:
    print("Error: This script requires pyobjc-framework-Quartz and pyobjc-framework-Cocoa on macOS.")
    sys.exit(1)

# GUI Dialog imports
try:
    from tkinter import messagebox, simpledialog, filedialog
    import tkinter as tk
    # Hide root window
    root = tk.Tk()
    root.withdraw()
except Exception:
    # Fallback if tkinter is missing
    class _FallbackDialogs:
        @staticmethod
        def showerror(title, message):
            print(f"ERROR: {title}: {message}")
        @staticmethod
        def showinfo(title, message):
            print(f"INFO: {title}: {message}")
    messagebox = _FallbackDialogs

# グローバル設定
kindle_window_title = 'Kindle' 
l_margin = 100
r_margin = 100
waitsec = 0.5  # ページめくり後の待機時間

def find_kindle_window():
    """
    Kindleウィンドウを検索して情報を返す (Quartz使用)
    Returns:
        dict: {'id': kCGWindowNumber, 'bounds': kCGWindowBounds, 'owner': ...} or None
    """
    options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
    windowList = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
    
    # 候補リスト (メインウィンドウっぽいやつを探す)
    candidates = []
    
    for win in windowList:
        owner = win.get('kCGWindowOwnerName', '') or ''
        name = win.get('kCGWindowName', '') or ''
        
        if 'Kindle' in owner:
            # ウィンドウサイズが小さすぎるものは除外 (ツールチップや不可視ウィンドウ)
            bounds = win.get('kCGWindowBounds')
            width = bounds.get('Width', 0)
            height = bounds.get('Height', 0)
            
            if width > 200 and height > 200:
                candidates.append(win)
                
    if not candidates:
        return None
        
    # 一番手前(レイヤーが上)のウィンドウ、もしくは一番大きいウィンドウを採用
    # 通常はリストの最初の方が手前
    return candidates[0]

def activate_kindle():
    """Kindleアプリをアクティブにする"""
    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    for a in apps:
        if a.localizedName() and 'Kindle' in a.localizedName():
            a.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
            time.sleep(1.0) # アクティブ化待ち
            return True
    return False

def capture_window_image(window_id):
    """
    指定されたWindowIDの内容をキャプチャする (他のウィンドウが重なっていても無視される)
    Returns:
        numpy array (BGR format for OpenCV)
    """
    # kCGWindowListOptionIncludingWindow: 指定したウィンドウIDを含む (そのウィンドウ自身のみ撮る)
    image_ref = Quartz.CGWindowListCreateImage(
        Quartz.CGRectNull,
        Quartz.kCGWindowListOptionIncludingWindow,
        window_id,
        Quartz.kCGWindowImageBoundsIgnoreFraming | Quartz.kCGWindowImageNominalResolution
    )
    
    if image_ref is None:
        return None

    width = Quartz.CGImageGetWidth(image_ref)
    height = Quartz.CGImageGetHeight(image_ref)
    
    # ピクセルデータを取得
    elapsed_time = 0
    provider = Quartz.CGImageGetDataProvider(image_ref)
    data = Quartz.CGDataProviderCopyData(provider)
    
    # numpy配列に変換 (BGRA format usually)
    # Note: CGImage usually returns BGRA or RGBA. converting to a buffer.
    # Buffer is byte array.
    
    # Create numpy array from buffer
    # Note: This handles standard 32-bit images
    # Check bits per pixel if necessary, but usually standard on mac
    
    img_data = np.frombuffer(data, dtype=np.uint8)
    
    # Reshape (Height, Width, 4 bytes)
    try:
        img_data = img_data.reshape((height, width, 4))
    except ValueError:
        # 解像度やフォーマットが違う場合のフォールバック (稀)
        return None

    # アルファチャンネルを除去してRGB/BGRにする
    # Mac Quartz often gives BGRA. OpenCV uses BGR.
    # So we want first 3 channels if it is BGR. 
    # Let's inspect channel order or just assume BGRA for now and convert to BGR.
    # Usually capture is BGRA.
    
    img_bgr = img_data[:, :, :3]
    return img_bgr

def find_content_boundaries(img):
    """
    画像内のコンテンツ境界を検出 (Cannyエッジ検出 + 射影プロファイル法)
    色ベースの単純判定ではなく、エッジの密度でコンテンツ領域を特定する
    """
    h, w, _ = img.shape
    
    # 1. グレースケール変換
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Cannyエッジ検出 (閾値は調整が必要かもしれません)
    # 文字や図形のエッジを抽出 -> 感度を上げて微細な文字も拾うようにする
    edges = cv2.Canny(gray, 10, 50)
    
    # 3. 垂直射影プロファイル (列ごとのエッジ画素値の合計)
    # axis=0 で縦方向に圧縮 -> 各X座標のエッジ強度合計
    v_profile = np.sum(edges, axis=0)
    
    # 4. コンテンツが存在する範囲を特定
    # ノイズ除去のため、ある程度の強度がある列のみを有効とする
    # 画像高さ * 255(白) * 割合 -> 閾値を下げて少しでも何かあれば残す
    threshold = h * 255 * 0.001 # 0.1%程度のエッジがあれば有効とみなす
    
    valid_columns = np.where(v_profile > threshold)[0]
    
    if len(valid_columns) == 0:
        # エッジがほとんどない（真っ白なページなど）
        return 0, w
        
    lft = valid_columns[0]
    rht = valid_columns[-1]
    
    # 5. マージン適用と範囲チェック
    lft = max(0, lft - l_margin)
    rht = min(w, rht + r_margin)
    
    return lft, rht

def send_background_key(pid, key_string):
    """
    非アクティブなウィンドウ(プロセス)にキーイベントを送る
    key_string: 'right', 'left', 'space'
    """
    # Key Codes for macOS
    kVK_LeftArrow = 123
    kVK_RightArrow = 124
    kVK_Space = 49
    
    if key_string == 'space':
        code = kVK_Space
    elif key_string == 'left':
        code = kVK_LeftArrow
    else:
        # Default to right
        code = kVK_RightArrow
    
    # Event source
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    
    # Key Down & Up
    d = Quartz.CGEventCreateKeyboardEvent(src, code, True)
    u = Quartz.CGEventCreateKeyboardEvent(src, code, False)
    
    # Post to PID
    Quartz.CGEventPostToPid(pid, d)
    time.sleep(0.05)
    Quartz.CGEventPostToPid(pid, u)

def capture_and_save_pages(window_info, title, base_dir):
    """メインループ: キャプチャ -> ページめくり -> 保存"""
    window_id = window_info['kCGWindowNumber']
    pid = window_info.get('kCGWindowOwnerPID')
    
    # 保存先作成
    target_dir = osp.join(base_dir, title)
    os.makedirs(target_dir, exist_ok=True)
    
    page = 1
    
    # 初期画像取得
    img = capture_window_image(window_id)
    if img is None:
        print("Failed to capture initial image.")
        return 0
        
    lft, rht = find_content_boundaries(img)
    
    # 1ページ目保存
    crop = img[:, lft:rht]
    filename = osp.join(target_dir, f"{page:03d}.png")
    cv2.imwrite(filename, crop)
    print(f"Page {page:03d} saved.")
    
    old_img = crop
    
    # ページめくりキー (Spaceキーは和書/洋書問わず「進む」動作になることが多い)
    # これにより逆走問題を回避する
    direction = 'space' 
    
    consecutive_no_change = 0
    max_retries = 3
    
    while True:
        # キー送信 (バックグラウンドのKindleプロセスへ)
        if pid:
            send_background_key(pid, direction)
        else:
            # PIDが取れない場合のフォールバック(アクティブウィンドウへ)
            pag.press(direction)
            
        time.sleep(waitsec)
        
        # 新しい画像をキャプチャ
        new_full = capture_window_image(window_id)
        if new_full is None:
            print("Capture failed, retrying...")
            time.sleep(1)
            continue
            
        new_crop = new_full[:, lft:rht]
        
        # 画像比較
        if np.array_equal(old_img, new_crop):
            # 変化なし
            consecutive_no_change += 1
            print(f"No change detected ({consecutive_no_change}/{max_retries})")
            
            if consecutive_no_change >= max_retries:
                # Spaceキーで進まない＝終端とみなす
                print("End of book detected.")
                break
        else:
            # 変化あり
            consecutive_no_change = 0
            page += 1
            filename = osp.join(target_dir, f"{page:03d}.png")
            cv2.imwrite(filename, new_crop)
            print(f"Page {page:03d} saved.")
            old_img = new_crop
            
    return page

def main():
    root_dir = os.getcwd()
    
    # Kindleを探す
    win_info = find_kindle_window()
    if not win_info:
        messagebox.showerror("エラー", "Kindle For Macのウィンドウが見つかりません。")
        return
        
    # アクティブ化コードを削除 (バックグラウンド処理のため)
    # if not activate_kindle():
    #     messagebox.showwarning("警告", "Kindleのアクティブ化に失敗しました。手動で前面にしてください。")
    
    # タイトル入力 (省略時は日付)
    # タイトル設定 (形式: output/HASH)
    import secrets
    random_hash = secrets.token_hex(2) # 4 digits
    title = f"output/{random_hash}"
    
    save_folder = osp.join(root_dir, title)
    
    print(f"Target Window ID: {win_info.get('kCGWindowNumber')}")
    print(f"Title: {title}")
    
    # 実行前に少し待つ
    time.sleep(1)
    
    total = capture_and_save_pages(win_info, title, root_dir)
    
    messagebox.showinfo("完了", f"完了しました。\n合計: {total} ページ\n保存先: {save_folder}")

if __name__ == "__main__":
    main()
