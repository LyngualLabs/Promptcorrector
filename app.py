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

# Function to load the next text to review
def load_next_text():
    docs = db.collection("texts").where("Status", "==", "pending").limit(1).stream()
    for doc in docs:
        return doc.id, doc.to_dict()
    return None, None

# Function to save the review
def save_review(doc_id, review_data):
    db.collection("texts").document(doc_id).update(review_data)

# Function to get the count of completed reviews by the user
def get_review_count(username):
    docs = db.collection("texts").where("reviewer", "==", username).stream()
    return sum(1 for _ in docs)

# Check if username is in session_state, if not, prompt for it
if "username" not in st.session_state:
    st.session_state.username = None

if st.session_state.username is None:
    # Prompt user to enter their name
    st.title("Welcome to the Code-Switched Text Reviewer")
    st.write("Please enter your name to begin the review session.")
    username = st.text_input("Your Name")

    if st.button("Start Review Session"):
        if username:
            st.session_state.username = username  # Save the username in session_state
            st.rerun()  # Reload the app to proceed to the review section
else:
    # Display the user's name and review count in the sidebar
    st.sidebar.title("Reviewer")
    st.sidebar.write(f"Username: {st.session_state.username}")
    
    # Get and display the number of reviews completed by the user
    review_count = get_review_count(st.session_state.username)
    st.sidebar.write(f"Reviews Completed: {review_count}")

    # Main app layout for reviewing
    st.title("Code-Switched Text Reviewer")

    doc_id, text_data = load_next_text()
    if text_data:
        st.write("## Original Yoruba Text")
        st.write(text_data["Text"])
        st.write("## AI Code-Switched Text")
        st.write(text_data["CodeSwitchedText"])

        st.write("### Review Actions")
        action = st.radio("Choose Action", ["Approve", "Edit", "Reject"])

        if action == "Edit":
            edit_from = st.radio("Edit from:", ["Original Yoruba Text", "AI Code-Switched Text"])
            
            if edit_from == "Original Yoruba Text":
                edited_text = st.text_area("Edited Code-Switched Text", text_data["Text"])
            else:
                edited_text = st.text_area("Edited Code-Switched Text", text_data["CodeSwitchedText"])

        if st.button("Submit Review"):
            review_data = {
                "Status": action.lower(),
                "reviewer": st.session_state.username,
                "reviewed_text": edited_text if action == "Edit" else text_data["CodeSwitchedText"],
            }
            save_review(doc_id, review_data)
            
            st.success("Review submitted!")
            st.rerun()  # Reload to get the next text
    else:
        st.write("No more texts to review.")
