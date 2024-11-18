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

# Function to get the count of completed reviews by the user (excluding rejects)
def get_review_count(username):
    docs = db.collection("texts").where("reviewer", "==", username).where("Status", "in", ["approve", "edit"]).stream()
    return sum(1 for _ in docs)

# Check if username is in session_state, if not, prompt for it
if "username" not in st.session_state:
    st.session_state.username = None

if st.session_state.username is None:
    # Prompt user to enter their name
    st.title("Welcome to the Code-Switched Text Reviewer")
    st.write("Please enter your name to begin the review session.")
    username = st.text_input("Your Name")
    username = username.strip().lower()

    if st.button("Start Review Session"):
        if username.strip():
            st.session_state.username = username.lower().strip()  # Save the username in session_state
            st.rerun()  # Reload the app to proceed to the review section
        else:
            st.warning("Please enter a valid name.")
else:
    # Display the user's name and review count in the sidebar
    st.sidebar.title("Reviewer")
    st.sidebar.write(f"Username: {st.session_state.username}")
    
    # Get and display the number of reviews completed by the user (excluding rejects)
    review_count = get_review_count(st.session_state.username)
    st.sidebar.write(f"Reviews Completed (Approves/Edits): {review_count}")

    # Add expandable guidelines for reviewers
    with st.expander("Reviewer Guidelines and Good Practices"):
        st.markdown("""
        ### Good Practices:
        1. Ensure the text is **high quality** and makes sense contextually.
        2. **Preserve diacritics** (e.g., accents on Yoruba words) where possible to maintain authenticity.
        3. Proper annotation is important. Reviewers who consistently annotate well will be drafted into the **second project phase**.
        4. If any text feels too challenging, feel free to discard it by pressing **Reject**.
        5. Remember: **Only Approves and Edits count** towards your progress; Rejected texts do not.
        """)

    # Main app layout for reviewing
    st.title("Code-Switched Text Reviewer")

    doc_id, text_data = load_next_text()
    if text_data:
        # Display the Yoruba text and AI code-switched text with increased font size and bold style
        st.markdown("## **Original Yoruba Text**")
        st.markdown(f"<p style='font-size:20px; font-weight:bold;'>{text_data['Text']}</p>", unsafe_allow_html=True)

        st.markdown("## **AI Code-Switched Text**")
        st.markdown(f"<p style='font-size:20px; font-weight:bold;'>{text_data['CodeSwitchedText']}</p>", unsafe_allow_html=True)

        # Review actions
        st.write("### Review Actions")
        action = st.radio("Choose Action", ["Approve", "Edit", "Reject"])

        # If editing, show text area for user input
        if action == "Edit":
            edit_from = st.radio("Edit from:", ["Original Yoruba Text", "AI Code-Switched Text"])
            
            if edit_from == "Original Yoruba Text":
                edited_text = st.text_area("Edited Code-Switched Text", text_data["Text"])
            else:
                edited_text = st.text_area("Edited Code-Switched Text", text_data["CodeSwitchedText"])

        # Submit button to save the review
        if st.button("Submit Review"):
            review_data = {
                "Status": action.lower(),
                "reviewer": st.session_state.username.lower().strip(),
                "reviewed_text": edited_text if action == "Edit" else text_data["CodeSwitchedText"] if action == "Approve" else None,
            }
            save_review(doc_id, review_data)
            
            st.success("Review submitted!")
            st.rerun()  # Reload to get the next text
    else:
        st.write("No more texts to review.")
