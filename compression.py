from flask import Flask, request, jsonify
from PIL import Image
import cv2
import os
import requests
import urllib.parse
import imghdr
import tempfile
import base64
from flask_cors import CORS 

app = Flask(__name__)
CORS(app)

def download_resource(url, local_path):
    response = requests.get(url)
    with open(local_path, 'wb') as f:
        f.write(response.content)

def upload_to_github(repo_owner, repo_name, branch, file_path, file_content, commit_message, access_token):
    api_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}'
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        current_commit_sha = response.json()['sha']
        data = {
            'message': commit_message,
            'content': base64.b64encode(file_content).decode('utf-8'),
            'sha': current_commit_sha,
            'branch': branch
        }

        response = requests.put(api_url, json=data, headers=headers)

        if response.status_code == 200:
            print("File updated successfully.")
        else:
            print(f"Failed to update file. Status code: {response.status_code}")
    elif response.status_code == 404:
        data = {
            'message': commit_message,
            'content': base64.b64encode(file_content).decode('utf-8'),
            'branch': branch
        }

        response = requests.put(api_url, json=data, headers=headers)

        if response.status_code == 201:
            print("File created successfully.")
        else:
            print(f"Failed to create file. Status code: {response.status_code}")
    else:
        print(f"Failed to check file existence. Status code: {response.status_code}")

def compress_image_auto(input_path, output_path, target_size):
    image = Image.open(input_path)

    original_width, original_height = image.size
    aspect_ratio = original_width / original_height
    target_width = 120

    while True:
        target_height = int(target_width / aspect_ratio)

        # Resize the image
        resized_image = image.resize((target_width, target_height), Image.ANTIALIAS)

        # Save the resized image in WEBP format
        resized_image.save(output_path, "WEBP", quality=70) 
        if os.path.getsize(output_path) <int(target_size) :
            break

        target_width -= 5
        if target_width <= 0:
            raise ValueError("Unable to meet target size. Consider adjusting target_size or quality.")

    print(f"Image compressed successfully. Target width: {target_width}")

def compress_video(input_path, output_path, target_size):
    cap = cv2.VideoCapture(input_path)
    width = int(cap.get(3))
    height = int(cap.get(4))

    fourcc = cv2.VideoWriter_fourcc(*"H264")  
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (width, height))

   
    quality = 85  
    target_quality = 50 
    max_iterations = 10  

    iteration = 0
    current_size = os.path.getsize(output_path)

    while cap.isOpened() and current_size > target_size and iteration < max_iterations:
        ret, frame = cap.read()
        if not ret:
            break

        _, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])

        out.write(cv2.imdecode(encoded_frame, 1))

        quality -= 5

        current_size = os.path.getsize(output_path)

        iteration += 1

    cap.release()
    out.release()

@app.route('/compress', methods=['POST'])
def compress_resource():
    input_url = request.json['input_url']
    target_size = request.json['target_size']
    github_repo_owner = 'yosraomran'
    github_repo_name = 'compressed_url'
    github_branch = 'main'
    github_file_path = 'yosra.webp'
    github_commit_message = 'Update compressed image'
    github_access_token = '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'  

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, 'C:\\Users\\HP\\Desktop\\compressed_url\\yoyo.png')
        output_path = os.path.join(temp_dir, 'C:\\Users\\HP\\Desktop\\compressed_url\\compressed_output.webp')

        download_resource(input_url, input_path)

        is_video = input_url.endswith(('.mp4', '.avi', '.mkv', '.mov'))

        if is_video:
            compress_video(input_path, output_path, target_size)
        else:
            compress_image_auto(input_path, output_path, target_size)

        # Upload the compressed image to GitHub
        with open(output_path, 'rb') as file:
            compressed_image_content = file.read()

        upload_to_github(github_repo_owner, github_repo_name, github_branch, github_file_path, compressed_image_content,
                         github_commit_message, github_access_token)


        input_size = os.path.getsize(input_path)
        output_size = os.path.getsize(output_path)
        input_dimensions = Image.open(input_path).size
        output_dimensions = Image.open(output_path).size


        _, ext = os.path.splitext(input_url)
        if is_video:
            original_format = 'VIDEO'
        else:
     
            with open(input_path, 'rb') as f:
                image_format = imghdr.what(None, h=f.read())
            original_format = image_format.upper() if image_format else 'UNKNOWN'

    compressed_url =f'https://raw.githubusercontent.com/{github_repo_owner}/{github_repo_name}/{github_branch}/{github_file_path}'
    response_data = {
        'input_size': input_size,
        'output_size': output_size,
        'input_dimensions': input_dimensions,
        'output_dimensions': output_dimensions,
        'input_format': original_format,
        'output_format': 'WEBP',
        'compressed_url': compressed_url
    }

    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)
