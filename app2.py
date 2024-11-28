import streamlit as st
from firebase_admin import credentials, firestore, initialize_app, _apps
import json
import os

# Initialize Firebase if it hasn't been initialized yet
firebase_secrets = json.loads(os.environ['firebase_credentials'])
if not _apps:
    cred = credentials.Certificate(firebase_secrets)
    initialize_app(cred)

db = firestore.client()

# Function to load the next review item
def load_next_text():
    # Fetch the next unreviewed text from Firestore
    docs = db.collection("stage_two_reviews").where("Status", "==", "pending").limit(1).stream()
    for doc in docs:
        return doc.id, doc.to_dict()
    return None, None

# Function to save the review decision
def save_review(doc_id, review_data):
    db.collection("stage_two_reviews").document(doc_id).update(review_data)

# Function to get the count of reviews done by the reviewer
def get_review_count(username):
    docs = db.collection("stage_two_reviews").where("reviewer", "==", username).stream()
    return sum(1 for _ in docs)

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
            st.rerun()  # Reload the app to proceed to the review section
else:
    # Display the username and review count in the sidebar
    st.sidebar.title("Senior Reviewer")
    st.sidebar.write(f"Username: {st.session_state.username}")

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