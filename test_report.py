import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image as RLImage

filepath = "test_image.pdf"
doc = SimpleDocTemplate(filepath, pagesize=letter)
story = []

snapshot_path = r"D:\CNN-SNN\neuroguard-ai\snapshots\stranger_0082e935.jpg"
print(f"Exists? {os.path.exists(snapshot_path)}")

if os.path.exists(snapshot_path):
    img = RLImage(snapshot_path)
    story.append(img)
    
doc.build(story)
print("PDF Built successfully.")
