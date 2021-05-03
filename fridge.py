from nameko.web.handlers import http
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.editor import AudioFileClip, VideoFileClip
from pysndfx import AudioEffectsChain
import os
import json
import math
import requests
import tempfile
import youtube_dl

class FridgeService:
    """
    Takes care of creating videos
    """
    name = 'fridge_service'

    @http('POST', '/freeze')
    def freeze(self, request):
        """
        Creates a video and uploads it to weed
        """
        video = json.loads(request.form['video'])

        # create temporary directory 
        dir = tempfile.mkdtemp(dir='/tmp')

        # download audio
        with youtube_dl.YoutubeDL({
            'format': 'bestaudio/best',
            'outtmpl': dir + '/%(id)s.%(ext)s'
        }) as ydl:
            ydl.download([video['song']])

        audio_path = dir + '/' + os.listdir(dir)[0]

        # download background
        extension = video['background'].split('.')[-1]

        if extension == 'gifv':
            extension = 'gif'

        is_gif = extension == 'gif'

        background = requests.get(video['background'])
        background_path = dir + '/background.' + extension

        with open(background_path, 'wb') as file:
            file.write(background.content)

        # slow down audio
        fx = AudioEffectsChain().speed(video['speed'])

        if video['speed'] != 1:
            fx = AudioEffectsChain().speed(video['speed'])

        if video['reverb']:
            fx = fx.reverb()

        fx(audio_path, dir + '/edited.mp3')

        # create video
        audio = AudioFileClip(dir + '/edited.mp3')
        image = VideoFileClip(background_path)

        if is_gif:
            loops = math.trunc(audio.duration / image.duration)
            image = image.loop(n=loops)

        final = CompositeVideoClip([image], size=image.size)
        final = final.set_audio(audio)
        final = final.set_duration(audio.duration)

        # TODO: make fps and bitrate configurable
        final.write_videofile(dir + '/out.mp4', fps=30, codec='mpeg4', bitrate='12000k')

        data = requests.post('http://0.0.0.0:11880/upload', data={'path': dir + '/out.mp4', 'video': json.dumps(video)})

        return data.text

    @http('POST', '/upload')
    def upload(self, request):
        """
        Uploads a video to youtube
        """

        video = json.loads(request.form['video'])
        path = request.form['path']

        print(path)

        title = video['artist'] + ' ~ ' + video['title'] + ' ' + video['title_adlib']
        description = title + '\n\n'

        if not video['social'] == {}:
            description += 'follow ' + video['artist'] + '\n'

            for k, v in video['social'].items():
                description += v + '\n'
   
        description += '\nsubscribe and turn on the notifications to not miss out on the freshest slowed & reverb edits'

        cmd = 'youtubeuploader -headlessAuth -title \'' + title + '\' -description \'' + description + '\' -secrets ~/.client_secrets.json -filename ' + path
        os.system(cmd)

        return video
