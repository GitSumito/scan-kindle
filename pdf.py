
import os
import argparse
from PIL import Image
from reportlab.pdfgen import canvas
import sys

def image_to_pdf(folder_path, output_pdf_path):
    """
    指定フォルダ内の画像をPDFに変換する関数
    """
    # 画像ファイルの取得とソート
    try:
        image_files = [f for f in os.listdir(folder_path) 
                       if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        image_files.sort()
    except FileNotFoundError:
        print(f"Error: Folder not found: {folder_path}")
        return False

    if not image_files:
        print(f"Error: No image files found in {folder_path}")
        return False

    # PDFの作成
    # ディレクトリ作成
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    
    c = canvas.Canvas(output_pdf_path)
    total_files = len(image_files)
    
    print(f"Converting {total_files} images to {output_pdf_path}...")

    for i, image_file in enumerate(image_files, 1):
        # 画像の読み込みとPDFページの作成
        full_path = os.path.join(folder_path, image_file)
        try:
            img = Image.open(full_path)
            width, height = img.size
            c.setPageSize((width, height))
            c.drawImage(full_path, 0, 0, width, height)
            c.showPage()
            
            # 進捗表示 (CLI)
            print(f"Processed {i}/{total_files}: {image_file}")
            
        except Exception as e:
            print(f"Error processing {image_file}: {e}")
            continue

    try:
        c.save()
        print("Conversion complete!")
        return True
    except Exception as e:
        print(f"Error saving PDF: {e}")
        return False

def main():
    base_dir = "output"
    
    # outputディレクトリが存在しない場合
    if not os.path.isdir(base_dir):
        print(f"Directory '{base_dir}' does not exist.")
        return

    # output内のすべてのディレクトリをスキャン
    for item in os.listdir(base_dir):
        if item == ".DS_Store": continue
        
        folder_path = os.path.join(base_dir, item)
        
        # ディレクトリのみを対象
        if os.path.isdir(folder_path):
            hash_name = item
            output_pdf_path = os.path.join(base_dir, f"{hash_name}.pdf")
            
            # PDFがすでに存在するかチェック
            if os.path.exists(output_pdf_path):
                print(f"Skipping {hash_name}: PDF already exists.")
                continue
                
            print(f"Processing {hash_name}...")
            image_to_pdf(folder_path, output_pdf_path)

if __name__ == "__main__":
    main()
