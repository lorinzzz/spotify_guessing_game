import json
import requests
import random
import pickle
import webbrowser
from datetime import datetime
import os
import dotenv
dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)
from newuser import SignIn
from threading import Timer
import urllib.request
from PIL import ImageTk, Image
import tkinter as tk

class GuessingGame:
    def __init__(self):
        self.spotify_token = ""
        self.playlist_id = ""
        self.tracks = []
        self.track_id_arr = []
        self.playlists = []
        self.playlist_id_arr = []
        self.number_of_songs = 0
        self.track_offset = 0
        self.track_pos = 0
        self.device_names = []
        self.device_id_arr = []
        self.current_device_id = ""

    # find playlists and store the names and id into a list
    def find_playlists(self):
        query = "https://api.spotify.com/v1/me/playlists?limit=50"
        response = requests.get(query, headers={"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.spotify_token)})
        response_json = response.json()
        for i in response_json["items"]: 
            self.playlists.append(i["name"])
            self.playlist_id_arr.append(i["id"])          

    # find songs from a playlist, and store all names and id into a list
    def find_songs(self):
        offset_tot = 1
        offset = 0
        # spotify only returns maximum 100 tracks, so we need to adjust the offset based on the total tracks and loop through if needed
        while offset <= offset_tot:
            query = "https://api.spotify.com/v1/playlists/{}/tracks?market=US&offset={}".format(self.playlist_id, offset)
            response = requests.get(query, headers={"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.spotify_token)})
            response_json = response.json()

            # get all track names and IDs 
            idx = 0
            for i in response_json["items"]: 
                if "restrictions" not in i["track"]:
                    self.tracks.append(i["track"]["name"]) 
                    self.track_id_arr.append(i["track"]["id"]) 

            if offset == 0:
                # get the total tracks from the playlist
                offset_tot = (int(response_json["total"]/100)) * 100
            offset += 100    

        self.number_of_songs = len(self.tracks)

    # refresh token handler 
    def call_refresh(self):
        refresh = 1
        # check if refresh pickle file exists 
        file_exists = os.path.isfile('refresh.pckl')
        if file_exists:
            # get date from file and find how many minutes has passed 
            file = open('refresh.pckl', 'rb')
            last_refresh = pickle.load(file)
            minutes_diff = (datetime.now() - last_refresh).total_seconds() / 60.0
            if minutes_diff <= 59.0:
                # don't refresh if time isn't over 59 minutes
                print("Token last refreshed: " + str(minutes_diff) + " minutes ago, no need to refresh.")
                refresh = 0
            file.close

        if refresh == 1:
            # grab new temp access token
            file = open('refresh.pckl', 'wb')
            now = datetime.now()
            self.spotify_token = self.refresh()
            os.environ['temp_token'] = self.spotify_token
            dotenv.set_key(dotenv_file, "temp_token", os.environ['temp_token'])
            pickle.dump(now, file)
            file.close
            print("Token refreshed!")
        elif refresh == 0:
            # reuse previous temp access token
            self.spotify_token = os.environ.get('temp_token')
            print("Reusing previous access token!")

    # refresh handler 
    def refresh(self):
        query = "https://accounts.spotify.com/api/token"
        response = requests.post(query,
                                 data={"grant_type": "refresh_token",
                                       "refresh_token": os.environ.get('refresh_token')},
                                 headers={"Authorization": "Basic " + os.environ.get('base_64')})
        response_json = response.json()
        return response_json["access_token"]

    # change user with URL as input from user containing the auth code 
    def change_user(self, url = ""):
        # get a new refresh token, and save to .env
        new_token_caller = SignIn()
        os.environ['refresh_token'] = new_token_caller.get_token(url)
        dotenv.set_key(dotenv_file, "refresh_token", os.environ['refresh_token'])
        # call refresh to get new temp access token, pickle the refresh time, then find all devices and playlists from user
        self.spotify_token = self.refresh()
        os.environ['temp_token'] = self.spotify_token
        dotenv.set_key(dotenv_file, "temp_token", os.environ['temp_token'])
        file = open('refresh.pckl', 'wb')
        now = datetime.now()
        pickle.dump(now, file)
        file.close
        self.find_playlists
        self.get_devices      

    # play song from playlist
    def play_song(self, replay = 0):
        query = "https://api.spotify.com/v1/me/player/play?device_id={}".format(self.current_device_id)
        if replay == 4 or replay == 0 or replay == 5:
            self.track_offset = random.randint(0, self.number_of_songs - 1) # get random track 
            track_length = self.get_track_length()
            self.track_pos = random.randint(int(track_length * 0.1), track_length - int(track_length * 0.1)) # get a random pos in track, but avoiding the first and last 10% of the song
        elif replay == 3:
            track_length = self.get_track_length()
            self.track_pos = random.randint(int(track_length * 0.1), track_length - int(track_length * 0.1)) 
        response = requests.put(query, headers={"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.spotify_token)}, json={"context_uri": "spotify:playlist:" + self.playlist_id, "offset": {"position": self.track_offset}, "position_ms": self.track_pos})
        return self.tracks[self.track_offset]

    # get the length of a track, so we can generate a random position in the song
    def get_track_length(self):
        track_id = self.track_id_arr[self.track_offset]
        query = "https://api.spotify.com/v1/audio-features/{}".format(track_id)
        response = requests.get(query, headers={"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.spotify_token)})
        response_json = response.json()
        return response_json["duration_ms"]

    # pause track
    def pause_track(self):    
        pause_query = "https://api.spotify.com/v1/me/player/pause"
        pause_response = requests.put(pause_query, headers={"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.spotify_token)})
    
    # change playlist 
    def change_playlist(self, playlist_num = 0):
        self.playlist_id = self.playlist_id_arr[playlist_num]
        self.tracks = []
        self.track_id_arr = []
        self.find_songs()
    
    # get all devices from user and store name and id into lists 
    def get_devices(self):
        query = "https://api.spotify.com/v1/me/player/devices"
        response = requests.get(query, headers={"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.spotify_token)})
        response_json = response.json()
        for x in response_json["devices"]:
            self.device_id_arr.append(x["id"])
            self.device_names.append(x["name"])
        # default device id    
        if len(self.device_id_arr) != 0: 
            self.current_device_id = self.device_id_arr[0]

    # sets playing device        
    def set_device(self, device_id = ""):
        self.current_device_id = self.device_id_arr[self.device_names.index(device_id)]

    # gets album art based on track in current playlist 
    def get_album_art(self, track_idx = 0):
        query = "https://api.spotify.com/v1/tracks/{}?market=US".format(self.track_id_arr[track_idx])
        response = requests.get(query, headers={"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.spotify_token)})
        response_json = response.json()
        return response_json["album"]["images"][1]["url"]

    # get artist name based on track in current playlist
    def get_artist(self, track_idx = 0):
        query = "https://api.spotify.com/v1/tracks/{}?market=US".format(self.track_id_arr[track_idx])
        response = requests.get(query, headers={"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.spotify_token)})
        response_json = response.json()    
        return response_json["album"]["artists"][0]["name"]       
    
    # returns the username of spotify account
    def get_user_name(self):
        query = "https://api.spotify.com/v1/me"
        response = requests.get(query, headers={"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.spotify_token)})
        response_json = response.json()    
        return response_json["display_name"]            

# function to handle the options of the music control buttons 
def change_replay_val(replay):
    correct_ans_pic.place_forget()
    incorrect_ans_pic.place_forget()
    album_pic.place_forget()
    song_info.place_forget()

    global play_length
    global penalty
    if replay == 3 or replay == 4:
        play_length = 2.0
        if replay == 3:
            penalty += 10
    if replay == 2:
        play_length += 2.0
        penalty += 15
    if replay == -1:
        quit()
    if replay == 1:
        penalty += 5
    current_song = a.play_song(replay)
    t = Timer(play_length, a.pause_track)
    t.start()
    if replay == 4:
        advanceGame(current_song)

# changes playlist, if play = 0 we are in the main menu, if play = 1 we are in game
def set_playlist(value, play = 0):
    a.change_playlist(a.playlists.index(value))
    if play == 1:
        current_song = a.play_song()
        advanceGame(current_song)
    if play == 0:
        start_button.place(x = 350, y = 450, anchor='center')
        playlist_info.configure(text = "Playlist has " + str(a.number_of_songs) + " songs")
    t = Timer(play_length, a.pause_track)
    t.start()

# fuction to handle the scoring, displayment of the correct answer, and whether the user answer was right or wrong
def checkAnswer(mc_answer = "", current_song = "", idx = 0):
    global score
    global songs_correct
    global songs_played
    global penalty
    songs_played += 1
    # get album art from curreont song
    urllib.request.urlretrieve(a.get_album_art(idx), "assets/art.png")
    art = ImageTk.PhotoImage(Image.open("assets/art.png"))
    album_pic.configure(image=art)
    album_pic.image = art
    album_pic.place(x = 170, y = 160, anchor='center')
    if current_song == mc_answer:
        correct_ans_pic.place(x = 535, y = 110, anchor='center')
        song_info.configure(text = current_song + " - " + a.get_artist(idx), wraplength = 300, bg = "black", fg = "green") # show correct answer in green
        song_info.place(x = 535, y = 250, anchor='center')
        correct_ans_pic.after(2000, lambda: change_replay_val(4))  
        score += (100 - penalty)
        songs_correct += 1
        penalty = 0
        score_display.configure(text = "Score: " + str(score))
        songs_correct_display.configure(text = "Songs Correct: " + str(songs_correct) + "/" + str(songs_played))      
    else:
        incorrect_ans_pic.place(x = 535, y = 110, anchor='center')
        song_info.configure(text = current_song + " - " + a.get_artist(idx), wraplength = 300, bg = "black", fg = "red") # show correct answer in red
        song_info.place(x = 525, y = 250, anchor='center')
        incorrect_ans_pic.after(2000, lambda: change_replay_val(4))
        score_display.configure(text = "Score: " + str(score))
        songs_correct_display.configure(text = "Songs Correct: " + str(songs_correct) + "/" + str(songs_played))  

# sets up multiple choice questions for every turn
def advanceGame(current_song = ""):
    mc_questions = ["", "", "", "", "", ""]
    mc_song_name = ["", "", "", "", "", ""]
    current_song_idx = a.tracks.index(current_song)
    correct_mc_idx = random.randint(0,5)
    idx = 0
    unique = 0
    # make sure we generate a random index that isn't the index of the current song
    while unique == 0:
        rand_idx = random.sample(range(0, a.number_of_songs - 1), 6)
        if current_song_idx not in rand_idx:
            unique = 1
    # populate the question and song name arrays
    while idx < 6:
        if idx == correct_mc_idx:
            mc_questions[idx] = current_song + " - " + a.get_artist(current_song_idx)
            mc_song_name[idx] = current_song
        else:
            mc_questions[idx] = a.tracks[rand_idx[idx]] + " - " + a.get_artist(rand_idx[idx])
            mc_song_name[idx] = a.tracks[rand_idx[idx]]
        idx += 1

    mc1_button.configure(text = mc_questions[0], command = lambda: checkAnswer(mc_song_name[0], current_song, current_song_idx))
    mc2_button.configure(text = mc_questions[1], command = lambda: checkAnswer(mc_song_name[1], current_song, current_song_idx))
    mc3_button.configure(text = mc_questions[2], command = lambda: checkAnswer(mc_song_name[2], current_song, current_song_idx))
    mc4_button.configure(text = mc_questions[3], command = lambda: checkAnswer(mc_song_name[3], current_song, current_song_idx))
    mc5_button.configure(text = mc_questions[4], command = lambda: checkAnswer(mc_song_name[4], current_song, current_song_idx))
    mc6_button.configure(text = mc_questions[5], command = lambda: checkAnswer(mc_song_name[5], current_song, current_song_idx))

# function to display initial screen for first time user setup
def change_show_new_user():
    a.change_user(redirect_uri_entry.get())
    display_user_name.configure(text = "Username: " + a.get_user_name())
    display_user_name.place(x = 350, y = 550, anchor = "center")
    # check if first_run flag is true 
    if os.environ.get('first_run') == '1': 
            os.environ['first_run'] = '0'
            dotenv.set_key(dotenv_file, "first_run", os.environ['first_run'])
            configure_button.place(x = 350, y = 450, anchor = "center")

# function for configure button command
def configure():
    hyperlink_button.place_forget()
    redirect_uri_entry.place_forget()
    enter_button.place_forget()  
    a.find_playlists()
    a.get_devices()
    to_main_menu()

# function to reset the scoring values
def resetValues():
    global score 
    global songs_correct
    global songs_played
    global penalty 
    score = 0
    songs_correct = 0
    songs_played = 0 
    penalty = 0    

# function to transition from the main menu to the start of the game
def startGame():
    resetValues()
    start_button.place_forget()
    welcome_text.place_forget()
    playlist_options.place_forget()
    playlist_info.place_forget()
    hyperlink_button.place_forget()
    redirect_uri_entry.place_forget()
    enter_button.place_forget()
    display_user_name.place_forget()
    device_options.place_forget()

    main_menu_button.place(x = 55, y = 780, anchor='center')
    score_display.configure(text = 'Score: 0')
    songs_correct_display.configure(text = 'Songs Correct: 0/0')
    replay_button.place(x = 100, y = 420, anchor='center')
    extend_and_replay_button.place(x = 266, y = 420, anchor='center')
    play_different_part_button.place(x = 434, y = 420, anchor='center')
    next_track_button.place(x = 600, y = 420, anchor='center')

    # updae the playlist options
    var2.set('Change Playlist')
    change_playlist['menu'].delete(0, 'end')
    for x in a.playlists:
        change_playlist['menu'].add_command(label=x, command = tk._setit(var2, x, lambda x: set_playlist(var2.get(), 1)))
    change_playlist.place(x = 350, y = 780, anchor='center')

    reset_game.place(x = 655, y = 780, anchor='center')
    songs_correct_display.place(x = 550, y = 370, anchor='center')
    score_display.place(x = 150, y = 370, anchor='center')
    current_song = a.play_song()
    t = Timer(play_length, a.pause_track)
    t.start()
    advanceGame(current_song)
    mc1_button.place(x = 200, y = 510, anchor='center')
    mc2_button.place(x = 500, y = 510, anchor='center')
    mc3_button.place(x = 200, y = 610, anchor='center')
    mc4_button.place(x = 500, y = 610, anchor='center')
    mc5_button.place(x = 200, y = 710, anchor='center')
    mc6_button.place(x = 500, y = 710, anchor='center')

# function to open link for the link button in the configure screen
def callback():
    webbrowser.open_new("https://accounts.spotify.com/en/authorize?client_id=f7030672f448481f85c1c90719ff5080&response_type=code&redirect_uri=https%3A%2F%2Fgoogle.com&scope=playlist-modify-public%20playlist-modify-private%20user-modify-playback-state%20playlist-read-private%20user-read-playback-state%20user-read-currently-playing%20playlist-read-collaborative")

# function for command to return to main menu
def to_main_menu():
    a.pause_track()
    resetValues()
    welcome_text.place(x = 350, y = 100, anchor='center')
    playlist_info.place(x = 350, y = 675, anchor='center')
    hyperlink_button.place(x = 200, y = 600, anchor='center')
    redirect_uri_entry.place(x = 350, y = 600, height = 25, width = 250, anchor='center')
    enter_button.place(x = 500, y = 600, anchor='center')
    display_user_name.configure(text = "Username: " + a.get_user_name())
    display_user_name.place(x = 350, y = 550, anchor = "center")

    # refresh the playlist options
    var1.set('Choose Playlist to Begin With')
    playlist_options['menu'].delete(0 , 'end')
    for x in a.playlists:
        playlist_options['menu'].add_command(label=x, command = tk._setit(var1, x, set_playlist))
    playlist_options.place(x = 350, y = 325, anchor = 'center')
    
    # refresh the the device options
    var3.set('Choose Device to Begin With')
    device_options['menu'].delete(0 , 'end')
    for x in a.device_names:
        device_options['menu'].add_command(label=x, command = tk._setit(var3, x, a.set_device))
    device_options.place(x = 350, y = 240, anchor = 'center')

    mc1_button.place_forget()
    mc2_button.place_forget()
    mc3_button.place_forget()
    mc4_button.place_forget()
    mc5_button.place_forget()
    mc6_button.place_forget()
    
    first_time_display.place_forget()
    instructions_display.place_forget()
    configure_button.place_forget()
    score_display.place_forget()
    songs_correct_display.place_forget()
    replay_button.place_forget()
    extend_and_replay_button.place_forget()
    play_different_part_button.place_forget()
    next_track_button.place_forget()
    main_menu_button.place_forget()
    change_playlist.place_forget()
    reset_game.place_forget()

# instantiate GuessingGame class
a = GuessingGame()
# initialize lists to a single element list, the OptionsMenu requires that a list is not empty, so these two lines will satisfy the condition for the time being
a.playlists = [""] 
a.device_names = [""]

replay = 0
current_song = ""
songs_played = 0
songs_correct = 0
score = 0
penalty = 0
play_length = 2.0 #default is 2000ms == 2seconds before pausing

# delcaring all tkinter objects
root = tk.Tk()
root.title("Spotify Guessing Game")

# window of 800x700
canvas = tk.Canvas(root, height = 800, width = 700, bg = "BLACK")
canvas.pack()

#### label, button, and options menu declaration/placement/configuration ####
configure_button = tk.Button(root, text="Configure", command = configure)
welcome_text = tk.Label(text = "Spotify Guessing Game", font=("Helvetica", 32), bg = "white", fg = "black")
playlist_info = tk.Label(text = "Playlist has 0 songs", font=("Helvetica", 24), bg = "black", fg = "white")


cross = tk.PhotoImage(file="assets/cross.png")
incorrect_ans_pic = tk.Label(root, image = cross, border = "0")
check = tk.PhotoImage(file="assets/check.png")
correct_ans_pic = tk.Label(root, image = check, border = "0")

song_info = tk.Label(font=("Helvetica", 18))
album_pic = tk.Label(root, border = "0")

score_display = tk.Label(root, text = 'Score: 0', font=("Helvetica", 18), bg = "black", fg = "white")
songs_correct_display = tk.Label(root, text = 'Songs Correct: 0/0', font=("Helvetica", 18), bg = "black", fg = "white")

first_time_display = tk.Label(text = "First Time Configuration", font=("Helvetica", 32), bg = "white", fg = "black")
instructions_display = tk.Label(text = "Press the link button, sign in and accept, then copy the link opened in the browser and paste it into the box and press enter", wraplength = 300, font=("Helvetica", 16), bg = "black", fg = "white")
hyperlink_button = tk.Button(root, text="Link", command = callback)
redirect_uri_entry = tk.Entry(root)
enter_button = tk.Button(root, text="Enter", command = lambda: change_show_new_user())
display_user_name = tk.Label(root, font=("Helvetica", 18), bg = "black", fg = "white", border = "0")

start_image = tk.PhotoImage(file="assets/rouded_red_button.png")
start_button = tk.Button(root, text="Start Game", image = start_image, command = startGame, bg = "black", border = "0")

main_menu_button = tk.Button(root, text="Main Menu", command = to_main_menu)
var1 = tk.StringVar(root)
var1.set('Choose Playlist to Begin With')
playlist_options=tk.OptionMenu(root, var1, *a.playlists, command = set_playlist)
playlist_options.configure(width = 35, height = 2, font=("Helvetica", 16))

replay_button = tk.Button(root, text="Replay", command = lambda: change_replay_val(1), font=("Helvetica", 15), width = 13)
extend_and_replay_button = tk.Button(root, text="Extend & Replay", command = lambda: change_replay_val(2),font=("Helvetica", 15), width = 13)
play_different_part_button = tk.Button(root, text="New Slice", command = lambda: change_replay_val(3),font=("Helvetica", 15), width = 13)
next_track_button = tk.Button(root, text="Next Track", command = lambda: change_replay_val(4),font=("Helvetica", 15), width = 13)

var2 = tk.StringVar(root)
var2.set('Change Playlist')
change_playlist=tk.OptionMenu(root, var2, *a.playlists, command = lambda x: set_playlist(var2.get(), 1))
change_playlist.configure(width = 35, height = 1,font=("Helvetica", 10))

var3 = tk.StringVar(root)
var3.set('Choose Device to Begin With')
device_options=tk.OptionMenu(root, var3, *a.device_names, command = a.set_device)
device_options.configure(width = 25, height = 1, font=("Helvetica", 14))   

reset_game = tk.Button(root, text="Reset Game", command = lambda: startGame(), font=("Helvetica", 10))

mc1_button = tk.Button(root, wraplength=250, height = 3, width = 20, font=("Helvetica", 16))
mc2_button = tk.Button(root, wraplength=250, height = 3, width = 20, font=("Helvetica", 16))
mc3_button = tk.Button(root, wraplength=250, height = 3, width = 20, font=("Helvetica", 16))
mc4_button = tk.Button(root, wraplength=250, height = 3, width = 20, font=("Helvetica", 16))
mc5_button = tk.Button(root, wraplength=250, height = 3, width = 20, font=("Helvetica", 16))
mc6_button = tk.Button(root, wraplength=250, height = 3, width = 20, font=("Helvetica", 16))

#### end label, button, and options menu declaration/placement/configuration ####

a.playlists = []
a.device_names = []
# handles if the app was run for the first time
if os.environ.get('first_run') == '1':   
    hyperlink_button.place(x = 200, y = 400, anchor='center')
    redirect_uri_entry.place(x = 350, y = 400, height = 25, width = 250, anchor='center')
    enter_button.place(x = 500, y = 400, anchor='center')
    first_time_display.place(x = 350, y = 100, anchor = 'center')
    instructions_display.place(x = 350, y = 275, anchor = 'center')
else:
    a.call_refresh()
    a.get_devices()
    a.find_playlists()
    to_main_menu()

root.mainloop()
