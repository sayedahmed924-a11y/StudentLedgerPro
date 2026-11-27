from PIL import Image, ImageDraw

img = Image.new('RGBA', (256, 256), color=(0, 0, 0, 0))
d = ImageDraw.Draw(img)

# رسم دائرة زرقاء رسمية
d.ellipse([10, 10, 246, 246], fill='#1e3a8a')

# رسم ورقة السجل البيضاء
d.rectangle([60, 50, 196, 206], fill='#ffffff')
d.rectangle([75, 80, 181, 95], fill='#3b82f6')
d.rectangle([75, 115, 181, 125], fill='#94a3b8')
d.rectangle([75, 140, 181, 150], fill='#94a3b8')
d.rectangle([75, 165, 135, 175], fill='#ef4444')

img.save('app_icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("✅ تم إنشاء ملف الأيقونة app_icon.ico بنجاح!")