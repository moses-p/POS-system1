from mailjet_rest import Client

# Your Mailjet API credentials
api_key = '803bd6af0cae2a48b4b00e8f57f6b323'
api_secret = '63a355ea51e645e07e7e4cb056de8f33'

mailjet = Client(auth=(api_key, api_secret), version='v3')

# 1. Create or get the contact list
contact_list_name = "POS System Launch"
result = mailjet.contactslist.create(data={'Name': contact_list_name})
if result.status_code == 201:
    contact_list_id = result.json()['Data'][0]['ID']
    print(f"Contact list '{contact_list_name}' created with ID: {contact_list_id}")
else:
    # If already exists, fetch the list ID
    if result.status_code == 400 and 'already exists' in str(result.json()).lower():
        # Get all contact lists and find the one with the correct name
        lists_result = mailjet.contactslist.get()
        if lists_result.status_code == 200:
            found = False
            for l in lists_result.json()['Data']:
                if l['Name'] == contact_list_name:
                    contact_list_id = l['ID']
                    found = True
                    print(f"Using existing contact list '{contact_list_name}' with ID: {contact_list_id}")
                    break
            if not found:
                print(f"Contact list '{contact_list_name}' already exists but could not be found.")
                exit()
        else:
            print("Failed to retrieve contact lists:", lists_result.json())
            exit()
    else:
        print("Error creating contact list:", result.json())
        exit()

# 2. Add contacts to the list
contacts = [
    {"Email": "aqr256@gmail.com", "Name": "AQR256"},
    {"Email": "houseofvision8@gmail.com", "Name": "House of Vision"},
    {"Email": "arisegeniusug@gmail.com", "Name": "Arise Genius"},
    {"Email": "mosesharuna407@gmail.com", "Name": "Moses Haruna"},
]

for contact in contacts:
    # Add contact to Mailjet
    res = mailjet.contact.create(data={"Email": contact["Email"], "Name": contact["Name"]})
    if res.status_code not in [201, 400]:  # 400 means already exists
        print(f"Error adding contact {contact['Email']}: {res.json()}")
    # Add contact to the list
    res = mailjet.listrecipient.create(data={
        "ContactAlt": contact["Email"],
        "ListID": contact_list_id
    })
    if res.status_code not in [201, 400]:
        print(f"Error adding contact {contact['Email']} to list: {res.json()}")

print("Contacts added to the list.")

# 3. Create and send a personalized campaign
mj = Client(auth=(api_key, api_secret), version='v3.1')

messages = []
for c in contacts:
    messages.append({
        "From": {
            "Email": "givenwholesalers1@gmail.com",
            "Name": "Given Wholesalers"
        },
        "To": [{"Email": c["Email"], "Name": c["Name"]}],
        "Subject": "Introducing Our New Point of Sale System – Faster, Smarter, Better!",
        "HTMLPart": f"""
        <h2>Welcome to a New Shopping Experience!</h2>
        <p>Dear {c['Name']},</p>
        <p>
          We're excited to announce the launch of our brand new Point of Sale (POS) system at Given Wholesalers!<br>
          Our new system is designed to make your shopping experience faster, more secure, and more convenient.
        </p>
        <ul>
          <li><b>Faster Checkout:</b> Enjoy reduced wait times at the counter.</li>
          <li><b>Digital Receipts:</b> Get your receipts sent directly to your email.</li>
          <li><b>Loyalty Program:</b> Earn points with every purchase and redeem exciting rewards.</li>
          <li><b>Contactless Payments:</b> Pay with your card or mobile device for added safety.</li>
        </ul>
        <p>
          <b>Special Offer:</b><br>
          As a thank you for being a valued customer, we're offering <b>10% off your next purchase</b> when you use our new POS system.<br>
          Just mention this email at checkout!
        </p>
        <hr>
        <p>
          <b>Contact Us:</b><br>
          Email: <a href=\"mailto:givenwholesalers1@gmail.com\">givenwholesalers1@gmail.com</a><br>
          Phone: 0782 413668
        </p>
        <p style=\"font-size:small;color:gray;\">
          If you no longer wish to receive these emails, simply reply with \"Unsubscribe\".
        </p>
        <p>
          Thank you for choosing Given Wholesalers.<br>
        </p>
        """,
        "CustomID": "POSSystemCampaign"
    })

data = {'Messages': messages}

result = mj.send.create(data=data)
print(result.status_code)
print(result.json()) 