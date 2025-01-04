import streamlit as st
from firebase_admin import credentials, firestore, initialize_app, _apps
import json
import os
# import dotenv
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt


# dotenv.load_dotenv()

openai_api_key = os.environ['openai_key']

# Initialize Firebase if it hasn't been initialized yet
firebase_secrets = json.loads(os.environ['firebase_credentials'])
if not _apps:
    cred = credentials.Certificate(firebase_secrets)
    initialize_app(cred)

db = firestore.client()

# Function to load the next review item
def load_next_text():
    docs = db.collection("stage_two_reviews").where("Status", "==", "pending").limit(1).stream()
    for doc in docs:
        return doc.id, doc.to_dict()
    return None, None

# Function to save the review decision
def save_review(doc_id, review_data):
    review_data["Timestamp"] = datetime.utcnow()  # Add a timestamp to the review
    db.collection("stage_two_reviews").document(doc_id).update(review_data)

# Function to get the count of reviews done by the reviewer
def get_review_count(username):
    docs = db.collection("stage_two_reviews").where("reviewer", "==", username).stream()
    return sum(1 for _ in docs)

# Function to get the history of prompts reviewed by the user
def get_review_history(username, limit):
    docs = db.collection("stage_two_reviews").where("reviewer", "==", username).stream()
    history = []
    for doc in docs:
        data = doc.to_dict()
        if not data.get("pulled", False) and data.get("Timestamp") is not None:  # Filter out documents where "pulled" is True or Timestamp is None
            history.append({
                "doc_id": doc.id,
                "OriginalText": data.get("OriginalText"),
                "CodeSwitchedText": data.get("CodeSwitchedText"),
                "reviewed_text": data.get("reviewed_text"),
                "Status": data.get("Status"),
                "Timestamp": data.get("Timestamp")
            })
    # Sort history by Timestamp in descending order and limit results
    sorted_history = sorted(history, key=lambda x: x["Timestamp"], reverse=True)
    return sorted_history[:limit]

# Function to update a specific review
def update_review(doc_id, edited_text):
    db.collection("stage_two_reviews").document(doc_id).update({
        "reviewed_text": edited_text,
        "Timestamp": datetime.utcnow()
    })

# Function to fetch review data for analytics
def fetch_review_data():
    docs = db.collection("stage_two_reviews").stream()
    data = []
    for doc in docs:
        record = doc.to_dict()
        if not record["pulled"]:
            data.append({
                "reviewer": record.get("reviewer", "unreviewed"),
                "Status": record["Status"]
            })
    data = pd.DataFrame(data)
    data["reviewer"] = data["reviewer"].str.strip()
    return data

# Streamlit App Layout
if "username" not in st.session_state:
    st.session_state.username = None

if st.session_state.username is None:
    # Prompt user to enter their name
    st.title("Welcome to the Senior Reviewer App")
    st.write("Please enter your name to begin the review session.")
    username = st.text_input("Your Name").lower()

    if st.button("Start Review Session"):
        if username:
            st.session_state.username = username  # Save the username in session_state
            from utils import generate_speech, play_audio, rephrase_text
            greeting = f"Hey! {username.split()[0]} Welcome back. Happy prompt reviewing. Godspeed"
            greeting = rephrase_text(openai_api_key,greeting)
            generate_speech(greeting,openai_api_key=openai_api_key, output_file= "welcome.mp3")
            play_audio("welcome.mp3")
            st.rerun()  # Reload the app to proceed to the review section
else:
    # Display the username and review count in the sidebar
    st.sidebar.title("Senior Reviewer")
    st.sidebar.write(f"Username: {st.session_state.username}")

    # Navigation Menu
    page = st.sidebar.radio("Navigate", ["Review", "History", "Analytics"])

    if page == "Review":
        # Get the review count for the current reviewer
        review_count = get_review_count(st.session_state.username)
        st.sidebar.write(f"Reviews Completed: {review_count}")

        # Load the next unreviewed text
        doc_id, text_data = load_next_text()

        if text_data:
            # Display the Original Text, Code-Switched Text, and Creator's Name
            st.title("Text Review")
            st.write("#### Original Text")
            st.write("###### " + text_data["OriginalText"])
            st.write("Code-Switched Text")
            st.write("##### " + text_data["CodeSwitchedText"])
            st.write("#### Creator's Name")
            st.write(text_data["CreatorName"])

            st.write("### Review Actions")
            action = st.radio("Choose Action", ["Approve", "Edit", "Reject"])

            # If the reviewer chooses "Edit", allow them to modify the text
            if action == "Edit":
                edited_text = st.text_area("Edited Code-Switched Text", text_data["CodeSwitchedText"])

            if st.button("Submit Review"):
                review_data = {
                    "Status": action.lower(),
                    "reviewer": st.session_state.username,
                    "reviewed_text": edited_text if action == "Edit" else text_data["CodeSwitchedText"],
                }
                save_review(doc_id, review_data)

                # Confirmation and auto-reload to fetch the next item
                st.success("Review submitted!")
                st.rerun()  # Reloads the app to show the next item
        else:
            st.write("No more texts to review.")

    elif page == "History":
        st.title("Review History")

        # User specifies the number of records to retrieve
        num_records = st.number_input("Number of records to retrieve:", min_value=1, max_value=100, value=10)

        # Fetch and display the review history
        history = get_review_history(st.session_state.username, num_records)

        if history:
            for record in history:
                st.write("---")
                st.write(f"**Original Text:** {record['OriginalText']}")
                st.write(f"**Code-Switched Text:** {record['CodeSwitchedText']}")
                st.write(f"**Your Reviewed Text:** {record['reviewed_text']}")
                st.write(f"**Status:** {record['Status']}")
                st.write(f"**Timestamp:** {record['Timestamp']}")

                # Option to edit the record
                if st.button(f"Edit Review - {record['doc_id']}"):
                    new_text = st.text_area("Edit the Code-Switched Text:", record['reviewed_text'], key=record['doc_id'])
                    if st.button(f"Save Changes - {record['doc_id']}"):
                        update_review(record['doc_id'], new_text)
                        st.success("Review updated successfully!")
                        st.rerun()
        else:
            st.write("No history available.")

    elif page == "Analytics":
        st.title("Reviewer Analytics")

        # Fetch review data and compute analytics
        review_data = fetch_review_data()
        if not review_data.empty:
            review_data =  review_data.fillna("unreviewed")
            original_review_data = review_data.copy()
            review_data = review_data[(review_data["reviewer"] != "unreviewed") & (review_data["Status"] != "reject")]
            status_count = review_data.groupby(['reviewer', 'Status']).size().unstack(fill_value=0)

            # Plotting
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = status_count.plot(kind='bar', stacked=True, ax=ax)

            # # Annotate bars with totals
            # for bar in bars.patches:
            #     ax.annotate(str(int(bar.get_height())),
            #                 (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            #                 ha='center', va='bottom', fontsize=9)

            # Add titles and labels
            plt.title("Review Status by Reviewer", fontsize=16)
            plt.xlabel("Reviewer", fontsize=12)
            plt.ylabel("Number of Reviews", fontsize=12)
            plt.xticks(rotation=0)
            plt.legend(title="Status", fontsize=10)
            plt.tight_layout()

            # Display the plot
            st.pyplot(fig)
            st.write("\n")
            st.write("Breakdown: Note that I've excluded your rejections, and this is data that has not been uploaded to the speech app")

            st.write(review_data["reviewer"].value_counts())
            # st.write(original_review_data)
            unreviewed_df = original_review_data[original_review_data["reviewer"]=="unreviewed"]
            # st.write(unreviewed_df)
            st.write("Sum total is: ", str(review_data["reviewer"].value_counts().sum()), "prompts")
            st.write("Unreviwed Prompts: ", str(len(unreviewed_df)), "prompts")


        else:
            st.write("No review data available for analytics.")
