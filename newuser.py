import requests
import os
import urllib.parse as urlparse
from urllib.parse import parse_qs

# takes a url containing the auth code and returns a refresh token

class SignIn:
    def get_token(self, url = ""):
        response1 = urlparse.urlparse(url)
        auth_code = parse_qs(response1.query)['code']

        headers = {
            'Authorization': 'Basic {}'.format(os.environ.get('base_64')),
        }

        data = {
        'grant_type': 'authorization_code',
        'code': '{}'.format(auth_code[0]),
        'redirect_uri': 'https://google.com'
        }


        response = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)
        response=response.json()
        return response['refresh_token'] 