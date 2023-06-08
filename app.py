from flask import Flask, render_template, request, redirect, flash, send_file, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2 import credentials
import json
import os
import traceback
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from fpdf import FPDF
import ssl
import google_auth_oauthlib.flow
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.errors
import zipfile

app = Flask(__name__)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('cert.pem', 'key.pem')
app.secret_key = 'secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'zip'}

CLIENT_SECRETS_FILE = 'client_secrets.json'
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly', 'https://www.googleapis.com/auth/youtube.force-ssl']


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def authenticate():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = request.base_url + '/callback'
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
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

    print(f"Search history: {search_history}")
    text = 'testing this'.join(search_history)
    print(f"Merged text: {text}")
    wordcloud = WordCloud(width=800, height=400).generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.tight_layout()

    wordcloud_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'wordcloud.png')
    plt.savefig(wordcloud_image_path)
    plt.close()

    return wordcloud_image_path


def generate_bar_chart(likes_count, comments_count):
    labels = ['Likes', 'Comments']
    counts = [likes_count, comments_count]

    plt.figure(figsize=(6, 4))
    plt.bar(labels, counts)
    plt.xlabel('Category')
    plt.ylabel('Count')
    plt.title('Likes and Comments')
    plt.tight_layout()

    bar_chart_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'bar_chart.png')
    plt.savefig(bar_chart_image_path)
    plt.close()

    return bar_chart_image_path


def generate_pdf(search_history, video_urls, likes_count, comments_count, bar_chart_image_path):
    output_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'report.pdf')

    try:
        # Create the PDF object
        pdf = FPDF()

        # Add a page and set the font for the title
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)

        # Add the title
        pdf.cell(0, 10, txt="YouTube Data Report", ln=True, align='C')

        # Add the search history section
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, txt="Search History", ln=True, align='L')
        pdf.set_font("Arial", "", 10)
        for query in search_history:
            pdf.cell(0, 8, txt=query, ln=True, align='L')

        # Add the video URLs section
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, txt="Video URLs", ln=True, align='L')
        pdf.set_font("Arial", "", 10)
        for url in video_urls:
            pdf.cell(0, 8, txt=url, ln=True, align='L')

        # Add the likes and comments section
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, txt="Likes and Comments", ln=True, align='L')
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 8, txt=f"Likes: {likes_count}", ln=True, align='L')
        pdf.cell(0, 8, txt=f"Comments: {comments_count}", ln=True, align='L')

        # Add the bar chart image
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, txt="Likes and Comments Bar Chart", ln=True, align='L')
        pdf.image(bar_chart_image_path, x=10, y=pdf.get_y() + 10, w=0, h=150)

        # Save the PDF
        pdf.output(output_pdf_path)

        return output_pdf_path

    except Exception as e:
        traceback.print_exc()
        return None




@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signin')
def signin():
    return authenticate()


@app.route('/signin/callback')
def signin_callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = request.base_url
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    session['credentials'] = creds.to_json()  # Serialize credentials to JSON

    # Authentication completed successfully, now redirect to the /process route
    return redirect('/process')


@app.route('/process', methods=['GET'])
def process():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"

    try:
        creds_info = session['credentials']
        creds_data = json.loads(creds_info)
        creds = Credentials.from_authorized_user_info(creds_data)

        youtube_service = build(api_service_name, api_version, credentials=creds)
        youtube = googleapiclient.discovery.build(api_service_name, api_version, credentials=creds)
        request = youtube.activities().list(part='snippet', mine=True)
        response = request.execute()

        print(response)
        print(youtube_service)

        search_history = ['']
        video_urls = ''
        likes_count = 0
        comments_count = 0

        # Fetch the entire YouTube history
        history_items = youtube_service.activities().list(
            part='snippet',
            maxResults=50,
            mine=True,
            fields='items(snippet/title),nextPageToken'
        ).execute()

        # print(history_items)

        while 'items' in history_items:
            print(history_items)
            for item in history_items['items']:
                # print(item[0].snippet)
                if 'resourceId' in item['snippet']:
                    video_id = item['snippet']['resourceId']['videoId']
                    video_info = youtube_service.videos().list(part='statistics', id=video_id).execute()

                    search_history += item['snippet']['title'] + '\n'
                    video_urls += f"https://www.youtube.com/watch?v={video_id}\n"

                    if 'likeCount' in video_info['items'][0]['statistics']:
                        likes_count += int(video_info['items'][0]['statistics']['likeCount'])

                    if 'commentCount' in video_info['items'][0]['statistics']:
                        comments_count += int(video_info['items'][0]['statistics']['commentCount'])

            if 'nextPageToken' in history_items:
                page_token = history_items['nextPageToken']
                history_items = youtube_service.activities().list(
                    part='snippet',
                    maxResults=50,
                    mine=True,
                    fields='items(snippet/title),nextPageToken',
                    pageToken=page_token
                ).execute()
            else:
                break

        # Generate data visualizations
        # wordcloud_image_path = generate_wordcloud(search_history)
        bar_chart_image_path = generate_bar_chart(likes_count, comments_count)

        # Generate the PDF report
        pdf_path = generate_pdf(search_history, video_urls, likes_count, comments_count,
                                bar_chart_image_path)

        if pdf_path:
            # Render the reports.html template and pass the PDF path
            return render_template('report.html', pdf_path=pdf_path)

        flash('Failed to generate the report', 'error')
        return redirect('/signin')

    except Exception as e:
        traceback.print_exc()
        flash('An error occurred during processing', 'error')
        return redirect('/')


if __name__ == '__main__':
    app.run(debug=True, host="localhost", port=5000, ssl_context=context)
