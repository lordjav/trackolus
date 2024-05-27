import os

def upload_image(image, SKU, directory, extensions):
    try:
        if image:
            extension = os.path.splitext(image.filename)[1].lower()
            if extension not in extensions:
                return ""
            image_name = SKU + extension
            image_route = os.path.join(directory, image_name)            
            image.save(image_route)
            return image_route
        
        else:
            return ""
    except Exception as e:
        return f"There was a problem uploading image: {e}"
