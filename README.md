# 006-music
**This is 006music's source code.**<br>
- It's free to use.
- If you want to continue developing it, yes you can.
## Getting Started
**Follow this step by step**
1. Download the release version
2. unzip file
3. edit token and prefix in config.toml
```sh
"token"="token" # the bot's token
"prefix"="-" # prefix used to denote commands
"app_id"="123456789" # Your application id

[music]
# Options for the music commands
"max_volume"=250 # Max audio volume. Set to -1 for unlimited.
"vote_skip"=true # whether vote-skipping is enabled
"vote_skip_ratio"=0.5 # the minimum ratio of votes needed to skip a song

```
4. install requirements.txt
```python
pip install -r requirements.txt
```
5. start bot
```python
python -m musicbot
```
