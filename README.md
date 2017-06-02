# pyWhatAuto

An IRC bot that can auto-download torrents, download on command, and provides a download button via a browser userscript.

Desperately in need of a rewrite.

# Setup instructions

## Get the files

### Git

Just use `git clone https://github.com/jimrollenhagen/pywhatauto.git` at the location you want to run your bot from.

### Zip

Grab the zip file from `https://github.com/jimrollenhagen/pywhatauto/archive/master.zip`.

#### Extract the files

If you are on a linux machine just run `unzip master.zip` and you'll end up with a directory called `pywhatauto-master`.

## Edit the configuration files

### setup.conf

Copy setup.conf.example to setup.conf

Setup the watch directory:
 
    torrentDir=/home/username/watch/
 
Setup the drive you want to show freespace on (usually the dir you download to):
 
    drive=/home/username/downloads/
 
Set the size of your download drive (in GB):
 
    limit=500
 
Set the percentage of your storage to use (stops downloading torrents when drive is this full):
 
    freePercent=5
 
Set log to 0 if you don't want to keep logs:
 
    log=0
 
Set chatter to 0 if you don't want to see channel traffic:
 
    chatter=0
 
Under [sites], enable the networks you want to watch, 1 is on, 0 is off.
 
`whatcd=0` to `whatcd=1` for example.

If you want to use the download button make sure to change the password and port for the web interface. For a more in-depth explanation of the download button read the "Download button" section below.

### credentials.conf

Copy credentials.conf.example to credentials.conf

In this file you'll have to add the credentials to the various sites and setup your bot on the IRC network. We'll take a look on how this'll look for What.CD:

    [whatcd]
    nickowner=99999@yourusername.yourclass.what.cd
    chanfilter=#whatbot
    username=yoursiteusername
    password=yoursitepassword
    botNick=yourusername|pyWHATbot
    ircKey=yourirckey
    nickServPass=yournickservpass
    watch=/home/username/watch/what
    
`nickowner`
Run /whois yourusername on the IRC network and you'll see the hostmask. That's what we need.

`chanfilter`
You don't have to change that. That's the channel where you can "talk" to your bot and issue commands.

`username`
Your What.CD username.

`password`
Your What.CD password.

`botNick`
The nick your bot will join the #whatbot channel and the announce channels.

`ircKey`
Your IRC key you setup in your What.CD user profile.

`nickServPass`
Your bot's NickServ password. You have to make sure your bot's IRC nick is registered. You can do that  by changing your nick and using the `REGISTER` command like this:

    /nick yourusername|pyWHATbot
    /msg nickserv register yourpassword your@email.com
    /whois yourusername|pyWHATbot

If you want to group your bot nick and your main account so you can use the same NickServ password for both accounts you'll have to run the following commands:

    /nick yourusername|pyWHATbot
    /nickserv group yourusername <your regular nickserv password>
    
    
`watch`
This is the directory you want the bot to store the `.torrent` files it snatched. This should also be your torrent client's watch directory.

### filters.conf

Copy filters.conf.example to filters.conf

This is the file where you tell your bot which releases it should grab for you.

To get an idea which options are possible please read the `filters.conf` included with this release.

**Examples:**

Here's an example to grab all of the 100% Log/Cue Flacs from the year 2014, if you wanted to download regardless of the year, just remove the line `year=2014`:
 
    [WHAT-2014FLAC]
    site=whatcd
    filterType=music
    active=1
    source=CD
    quality=Lossless
    format=FLAC
    cue=1
    log=1
    logper=100
    year=2014
    watch=/home/username/watch/what/
    
If you are just interested in specific artists you could add them like this. Note that regex must be prefixed with `@`:

    [WHAT-JAMS]
    site=whatcd
    filterType=music
    active=1
    artist=Widespread Panic
            Phish
            Furthur
            Trey Anastasio
            @Umphrey(.+)s McGee
            @Jerry Joseph.*
    format=FLAC
            MP3
    year=2014
    watch=/home/username/watch/what/
    
# Start the bot

To start the bot just run `python WHATauto.py` which is located in the pywhatauto directory. Make sure the python version you are using to execute it is < than 3 (Check with `python --version`). If your operating system defaults to a newer version you'll have to manually specify the version and start it like this: `python2.7 WHATauto.py`
 
Currently your bot will close the connection to the IRC network if you close your terminal. To keep it running in the background even if you close your terminal it's recommended to use something like `screen` or `tmux`.

To use screen type `screen -S nameofmyscreen` and press return. In the new screen you just opened just navigate to the place where your `WHATauto.py` is located and then run it like explained above. Now we'll have to detach the window with `ctrl` + `a` + `d`. You'll be back at the place where we started before you typed the `screen` command. If you want to list your screens running in the background just type `screen -ls` and you'll get a list of screens which'll look like this:

    There are screens on:
            8304.test       (Detached)
            27582.pywhatauto        (Detached)
    2 Sockets in /home/dewey/.screen.

To attach to a detached screen just type `screen -r 27582` and you'll be back at your bot's screen.

# Sending commands to the bot

If you want to get informations from your bot or issue download commands just join the same channel your bot is sitting in on the IRC net work and type `%help`. Your bot should now respond to your commands.

# Download button

If you want to use the pyWA download button to send torrents to your bot via your browser you'll need to install the user script located in your `pywhatauto-master` directory. It's called `button.user.js`.

The older (original) version can be found at  [userscripts-mirror.org](https://userscripts-mirror.org/scripts/show/85457).

Once the script is installed, you will need to visit your settings page on a gazelle based site and configure the script. All fields auto save.

![Settings preview](http://i.imgur.com/t1vPmSq.png)

The port and password of the web interface are configured in the `setup.conf`. The relevant bits looks like this:


    ;WEBUI password
    password=youwouldliketoknowthisone
    ;WEBUI port
    port=1337

The hostname can be an IP address or domain pointing towards your server.

# Support

If you are having troubles getting your bot to work just join `#whatbot` on the PTH IRC network.
