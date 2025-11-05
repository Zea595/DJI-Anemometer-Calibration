import requests

topic = "AEROSPACE_BCIT"
url = f"https://ntfy.sh/{topic}"

# Message Content
message = "Hello"

# Send Notification
response = requests.post(
    url,
    data=message.encode("utf-8")  # encode ensures emojis and UTF-8 text work fine
)

# Check response
if response.status_code == 200:
    print("✅ Notification successful!")
else:
    print(f"❌ Failed! Status: {response.status_code}, Response: {response.text}")