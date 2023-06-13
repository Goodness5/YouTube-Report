from flask import Flask, render_template, request, redirect, flash, send_file, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2 import credentials
import json
import os
import uuid
import time
import traceback
import requests
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.ticker import FuncFormatter
from io import BytesIO
from PIL import Image
import logging
from wordcloud import WordCloud
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import ssl
import csv
from bs4 import BeautifulSoup
import google_auth_oauthlib.flow
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.errors
import zipfile
from fpdf import FPDF
import matplotlib.image as mpimg
import pandas as pd

app = Flask(__name__)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

# UNCOMMENT THIS TO ENABLE GOOGLE AUTH AND UPDATE THE CLIENTSECRETS.JSON, CERT.PEM AND KEY.PEM WITH YOUR GOOGLE CLOUD CREDENTIALS
# context.load_cert_chain('cert.pem', 'key.pem')
app.secret_key = 'secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['STATIC_FOLDER'] = 'static'
app.config['ALLOWED_EXTENSIONS'] = {'zip'}

CLIENT_SECRETS_FILE = 'client_secrets.json'
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly',
          'https://www.googleapis.com/auth/youtube.force-ssl']


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# AUTHENTICATION FUNCTION TO ENABLE GOOGLE SIGN IN
def authenticate():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = request.base_url + '/callback'
    authorization_url, state = flow.authorization_url(
        access_type='offline', include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)


def extract_file(file_path, target_folder):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(target_folder)


def process_data(search_history, video_urls, likes_count, comments_count):
    search_history = search_history.split('\n')
    video_urls = video_urls.split('\n')
    likes_count = int(likes_count)
    comments_count = int(comments_count)
    return search_history, video_urls, likes_count, comments_count


def generate_wordcloud(search_history):
    if not search_history:
        default_text = "Default Text"  # Replace with your desired default text
        search_history = [default_text]

    text = ' '.join(search_history)
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.tight_layout()

    unique_filename = f"wordcloud_{uuid.uuid4().hex}.png"
    wordcloud_image_path = os.path.join(app.config['STATIC_FOLDER'], unique_filename)
    plt.savefig(wordcloud_image_path, bbox_inches='tight', pad_inches=0)
    plt.close()

    return wordcloud_image_path


def generate_bar_chart(likes_count, comments_count, watch_count, search_count):
    labels = ['Likes', 'Comments', 'Watch Count', 'Search Count']
    counts = [likes_count, comments_count, watch_count, search_count]
    colors = ['red', 'green', 'blue', 'orange']

    plt.figure(figsize=(8, 6))
    plt.bar(labels, counts, color=colors)
    plt.xlabel('Metrics', fontsize=12)
    plt.ylabel('Count', fontsize=12)
    plt.title('Metrics', fontsize=14)

    unique_filename = f"bar_chart_{uuid.uuid4().hex}.png"
    chart_image_path = os.path.join(app.config['STATIC_FOLDER'], unique_filename)
    plt.savefig(chart_image_path, bbox_inches='tight', pad_inches=0)
    plt.close()

    return chart_image_path


def generate_pie_chart(likes_count, comments_count, watch_count, search_count):
    labels = ['Likes', 'Comments', 'Watch Count', 'Search Count']
    counts = [likes_count, comments_count, watch_count, search_count]
    colors = ['skyblue', 'lightgreen', 'lightcoral', 'lightsalmon']

    # Create a wider figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Generate the pie chart without labels
    wedges, _ = ax.pie(counts, labels=[None] * len(counts), colors=colors, startangle=90)

    # Add padding between the components
    plt.setp(wedges, width=0.4)

    # Set the title
    ax.set_title('Number of likes, comments, watches, and search', fontsize=12)

    # Adjust the spacing between the pie chart and the labels
    ax.legend(wedges, labels, loc="best", bbox_to_anchor=(1, 0.5), fontsize=8)

    unique_filename = f"pie_chart_{uuid.uuid4().hex}.png"
    chart_image_path = os.path.join(app.config['STATIC_FOLDER'], unique_filename)
    plt.savefig(chart_image_path, bbox_inches='tight', pad_inches=0)
    plt.close()

    return chart_image_path






def generate_heatmap(playlists):
    num_videos = []
    for playlist in playlists:
        num_videos.extend([len(playlist['video_ids'])])

    data = np.array(num_videos).reshape(-1, 1)

    plt.figure(figsize=(8, 6))
    sns.heatmap(data, cmap='YlOrRd', annot=True, fmt='d', cbar=False)
    plt.title('Playlist Video Count', fontsize=14)
    plt.xlabel('Playlist', fontsize=12)
    plt.ylabel('Video Count', fontsize=12)

    unique_filename = f"heatmap_{uuid.uuid4().hex}.png"
    chart_image_path = os.path.join(app.config['STATIC_FOLDER'], unique_filename)
    plt.savefig(chart_image_path, bbox_inches='tight', pad_inches=0)
    plt.close()

    return chart_image_path


def generate_pdf(wordcloud_image_path, bar_chart_image_path, pie_chart_image_path, radar_chart_image_path, heatmap_image_path):
    pdf = FPDF()
    pdf.add_page()

    # Add word cloud image
    pdf.image(wordcloud_image_path, x=10, y=10, w=190, h=0)

    # Add bar chart image
    pdf.image(bar_chart_image_path, x=10, y=120, w=90, h=0)

    # Add pie chart image
    pdf.image(pie_chart_image_path, x=110, y=120, w=90, h=0)

    # Add heatmap image
    pdf.image(heatmap_image_path, x=10, y=220, w=90, h=0)

    # Create a radar chart for the remaining data
    pdf.image(radar_chart_image_path, x=110, y=220, w=90, h=0)

    unique_filename = f"output_{uuid.uuid4().hex}.pdf"
    pdf_path = os.path.join(app.config['STATIC_FOLDER'], unique_filename)

    pdf.output(pdf_path, 'F')

    return pdf_path




def generate_stacked_bar_chart(likes_count, comments_count, watch_count, search_count):
    # Define the categories and data for the stacked bar chart
    categories = ['Likes', 'Comments', 'Watch', 'Search']
    data = [likes_count, comments_count, watch_count, search_count]

    # Create the stacked bar chart
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.bar(categories, data[0], label='Category 1')
    for i in range(1, len(data)):
        ax.bar(categories, data[i], bottom=np.sum(data[:i], axis=0), label=f'Category {i+1}')

    # Set the labels and title
    ax.set_xlabel('Categories')
    ax.set_ylabel('Counts')
    ax.set_title('Stacked Bar Chart')
    ax.legend()

    unique_filename = f"stacked_bar_chart_{uuid.uuid4().hex}.png"
    stacked_bar_chart_image_path = os.path.join(app.config['STATIC_FOLDER'], unique_filename)
    plt.savefig(stacked_bar_chart_image_path)
    plt.close()

    return stacked_bar_chart_image_path






@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signin')
def signin():
    return authenticate()


@app.route('/signin/callback')
def signin_callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = request.base_url
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    session['credentials'] = creds.to_json()  # Serialize credentials to JSON

    # Authentication completed successfully, now redirect to the /process route
    return redirect('/process')


def csv_to_json(file_path):
    data = []
    with open(file_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            data.append(row)
    return data


def html_to_json(file_path):
    with open(file_path, 'r') as file:
        soup = BeautifulSoup(file, 'html.parser')
        data = []
        for item in soup.find_all('item'):
            item_data = {}
            for child in item.children:
                if child.name:
                    item_data[child.name] = child.text
            data.append(item_data)
    return data



# @DEV: THIS CODE WILL ONLY EXTRACT DATA FROM A STANDARD YOUTUBE TAKEOUT ZIPPED FILE, SUB STANDARD FILES ARE NOT SUPPORTED

def process_extracted_data(target_folder):
    search_history = []
    video_urls = []
    likes_count = 0
    comments_count = 0
    search_count= 0
    watch_count = 0
    playlists = []

    youtube_folder = os.path.join(target_folder, 'Takeout', 'YouTube and YouTube Music')
    if not os.path.isdir(youtube_folder):
        print(f"YouTube folder not found: {youtube_folder}")
        return search_history, video_urls, likes_count, comments_count, playlists, search_count

    # Process watch history
    watch_history_folder = os.path.join(youtube_folder, 'history')
    if not os.path.isdir(watch_history_folder):
        print(f"Watch history folder not found: {watch_history_folder}")
    else:
        history_file_path = os.path.join(watch_history_folder, 'watch-history.json')
        if os.path.isfile(history_file_path):
            try:
                with open(history_file_path, 'r') as file:
                    data = json.load(file)
                    for item in data:
                        watch_count +=1
                        if 'titleUrl' in item:
                            video_urls.append(item['titleUrl'])
            except FileNotFoundError:
                print(f"Watch history file not found: {history_file_path}")
            except json.JSONDecodeError:
                print(f"Error decoding JSON file: {history_file_path}")


    # Process search history
    search_history_folder = os.path.join(youtube_folder, 'history')
    if not os.path.isdir(search_history_folder):
        print(f"Search history folder not found: {search_history_folder}")
    else:
        history_file_path = os.path.join(search_history_folder, 'search-history.json')
        if os.path.isfile(history_file_path):
            try:
                with open(history_file_path, 'r') as file:
                    data = json.load(file)
                    if data:
                        search_history = [item['title'] for item in data if 'title' in item]
                        search_count = len(search_history)
                        # print(search_history)
            except FileNotFoundError:
                print(f"Search history file not found: {history_file_path}")
            except json.JSONDecodeError:
                print(f"Error decoding JSON file: {history_file_path}")

    # Process likes


    likes_folder = os.path.join(youtube_folder, 'playlists')
    if not os.path.isdir(likes_folder):
        print(f"Likes folder not found: {likes_folder}")
    else:
        likes_file_path = os.path.join(likes_folder, 'Liked videos.json')
        if os.path.isfile(likes_file_path):
            try:
                with open(likes_file_path, 'r') as file:
                    data = json.load(file)
                    if 'contents' in data:
                        likes_count = len(data['contents'])
            except FileNotFoundError:
                print(f"Likes file not found: {likes_file_path}")
            except json.JSONDecodeError:
                print(f"Error decoding JSON file: {likes_file_path}")
        else:
            likes_file_path_csv = os.path.join(likes_folder, 'Liked videos.csv')
            if os.path.isfile(likes_file_path_csv):
                try:
                    with open(likes_file_path_csv, 'r') as file:
                        csv_reader = csv.DictReader(file)
                        likes_count = sum(1 for row in csv_reader)
                        print(likes_count)
                except FileNotFoundError:
                    print(f"Likes file not found: {likes_file_path_csv}")
            else:
                print("No liked videos file found.")





    comments_folder = os.path.join(youtube_folder, 'my-comments')
    if not os.path.isdir(comments_folder):
        print(f"Comments folder not found: {comments_folder}")
    else:
        comment_files = os.listdir(comments_folder)
        for comment_file in comment_files:
            comment_file_path = os.path.join(comments_folder, comment_file)
            if os.path.isfile(comment_file_path):
                print("a file found", comment_file_path)
                try:
                    with open(comment_file_path, 'r') as file:
                        try:
                            data = json.load(file)
                            print(data)
                            if isinstance(data, list):
                                comments_count += len(data)
                        except json.JSONDecodeError:
                            # Handle non-JSON file formats
                            file_data = file.read()
                            if comment_file_path.endswith('.html'):
                                print('file ends with html')
                                with open(comment_file_path) as f:
                                    soup = BeautifulSoup(f, 'html.parser')
                                    
                                    # print('soup', soup)
                                # Process HTML file data
                                # Extract comments count from HTML
                                    comment_tags = soup.find_all('li')
                                for comment_tag in comment_tags:
                                    comment_text = comment_tag.get_text(strip=True)
                                    # print('comment:', comment_text)
                                    comments_count += 1
                            elif comment_file_path.endswith('.csv'):
                                # Process CSV file data
                                reader = csv.reader(file)
                                # Skip header row if present
                                next(reader, None)
                                # Count the comments
                                comments_count += sum(1 for _ in reader)
                            else:
                                print(f"Unsupported file format: {comment_file_path}")
                except FileNotFoundError:
                    print(f"Comments file not found: {comment_file_path}")


   
    # Process playlists
    playlists_folder = os.path.join(youtube_folder, 'playlists')
    if not os.path.isdir(playlists_folder):
        print(f"Playlists folder not found: {playlists_folder}")
    else:
        playlist_files = os.listdir(playlists_folder)
        playlists = []  # Store playlist data

        for playlist_file in playlist_files:
            playlist_file_path = os.path.join(playlists_folder, playlist_file)
            if os.path.isfile(playlist_file_path):
                try:
                    with open(playlist_file_path, 'r') as file:
                        if playlist_file_path.endswith('.csv'):
                            reader = csv.reader(file)
                            playlist_info = next(reader)  # Read the playlist information
                            video_ids = [row[0] for row in reader if row]  # Extract the video IDs
                            # Process the playlist information and video IDs as needed
                            # ...
                            playlist_data = {'playlist_info': playlist_info, 'video_ids': video_ids}
                            playlists.append(playlist_data)
                        elif playlist_file_path.endswith('.html'):
                            soup = BeautifulSoup(file, 'html.parser')
                            # Process the HTML file and extract playlist data
                            # ...
                        elif playlist_file_path.endswith('.json'):
                            data = json.load(file)
                            if 'contents' in data:
                                # Process the JSON data and extract playlist data
                                print('Extracting playlist')
                        else:
                            print(f"Unsupported file format: {playlist_file_path}")
                except FileNotFoundError:
                    print(f"Playlist file not found: {playlist_file_path}")

    print("processed data:")
    return search_history, video_urls, likes_count, comments_count, playlists, watch_count, search_count





@app.route('/process', methods=['GET', 'POST'])
def process():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"

    if request.method == 'POST':
        uploaded_file = request.files['file']
        # print(uploaded_file)
        if uploaded_file is None:
            flash('No file part', 'error')
            print("file error")
            return redirect(request.url)
        if uploaded_file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if allowed_file(uploaded_file.filename):
            # Save the uploaded file
            file_path = os.path.join(
                app.config['UPLOAD_FOLDER'], uploaded_file.filename)
            uploaded_file.save(file_path)

            # Extract the file contents
            target_folder = os.path.join(
                app.config['UPLOAD_FOLDER'], 'extracted')
            extract_file(file_path, target_folder)

            # Process the extracted data
            search_history, video_urls, likes_count, comments_count, playlists, watch_count, search_count= process_extracted_data(target_folder)

            # print('dataset are:',search_history, video_urls, likes_count, comments_count)

            # Generate data visualizations
            wordcloud_image_path = generate_wordcloud(search_history)
            pie_chart_image_path = generate_pie_chart(likes_count, comments_count, watch_count, search_count)
            bar_chart_image_path = generate_bar_chart(likes_count, comments_count, watch_count, search_count)
            radar_chart_image_path = generate_stacked_bar_chart(likes_count, comments_count, watch_count, search_count)

            # print(playlists)
            heatmap_image_path = generate_heatmap(playlists)

            # Generate the PDF report
            pdf_path = generate_pdf(wordcloud_image_path, bar_chart_image_path, pie_chart_image_path,radar_chart_image_path, heatmap_image_path)
            print(pdf_path)
            if pdf_path:
                # Render the report.html template and pass the PDF path
                print(pdf_path, heatmap_image_path, wordcloud_image_path, bar_chart_image_path, pie_chart_image_path, radar_chart_image_path)
                return render_template('report.html', pdf_path=pdf_path, heatmap_image_path=heatmap_image_path, wordcloud_image_path=wordcloud_image_path, bar_chart_image_path=bar_chart_image_path, pie_chart_image_path=pie_chart_image_path, radar_chart_image_path=radar_chart_image_path)

            flash('Failed to generate the report', 'error')
            return redirect('/')

        flash('Invalid file format', 'error')
        return redirect('/')

    # elif request.method == 'GET':
    #     if 'credentials' in session:
    #         try:
    #             creds_info = session['credentials']
    #             creds_data = json.loads(creds_info)
    #             creds = Credentials.from_authorized_user_info(creds_data)

    #             youtube_service = build(api_service_name, api_version, credentials=creds)
    #             youtube = googleapiclient.discovery.build(api_service_name, api_version, credentials=creds)
    #             activities_request = youtube.activities().list(part='snippet', mine=True)
    #             response = activities_request.execute()

    #             search_history = ['']
    #             video_urls = ''
    #             likes_count = 0
    #             comments_count = 0

    #             if 'items' in response:
    #                 for item in response['items']:
    #                     # print(item)
    #                     if 'resourceId' in item['snippet']:
    #                         video_id = item['snippet']['resourceId']['videoId']
    #                         print(video_id)
    #                         video_info = youtube_service.videos().list(part='statistics', id=video_id).execute()

    #                         search_history += item['snippet']['title'] + '\n'
    #                         video_urls += f"https://www.youtube.com/watch?v={video_id}\n"
    #                         print(video_urls)

    #                         if 'likeCount' in video_info['items'][0]['statistics']:
    #                             likes_count += int(video_info['items'][0]['statistics']['likeCount'])

    #                         if 'commentCount' in video_info['items'][0]['statistics']:
    #                             comments_count += int(video_info['items'][0]['statistics']['commentCount'])

    #             # Generate data visualizations
    #             # wordcloud_image_path = generate_wordcloud(search_history)
    #             bar_chart_image_path = generate_bar_chart(likes_count, comments_count)

    #             # Generate the PDF report
    #             pdf_path = generate_pdf(search_history, video_urls, likes_count, comments_count, bar_chart_image_path)

    #             if pdf_path:
    #                 # Render the reports.html template and pass the PDF path
    #                 return render_template('report.html', pdf_path=pdf_path)

    #             flash('Failed to generate the report', 'error')
    #             return redirect('/signin')

        #     except Exception as e:
        #         traceback.print_exc()
        #         flash('An error occurred during processing', 'error')
        #         return redirect('/')

        # flash('Please sign in first', 'error')
        # return redirect('/signin')

    else:
        flash('Method not allowed', 'error')
        return redirect('/')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
