import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re
from difflib import SequenceMatcher
import os
import cv2
import numpy as np
from datetime import datetime


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="AI Document Screening System",
    page_icon="🛂",
    layout="wide"
)


# =========================================================
# TITLE
# =========================================================

st.title("🛂 AI-Based Fake Identity & Document Screening System")

st.write(
    "AI-powered screening platform for document verification, "
    "tampering detection, identity verification, and risk assessment."
)


# =========================================================
# LOAD DATASET
# =========================================================

try:
    data = pd.read_csv("dataset.csv")
except Exception as e:
    st.error(f"Unable to load dataset.csv: {e}")
    st.stop()


# =========================================================
# DOCUMENT SELECTION & UPLOAD
# =========================================================

st.write("### 📄 Document Screening")

document_type = st.selectbox(
    "Select Document Type",
    [
        "Passport",
        "Visa",
        "National ID",
        "Driving License",
        "Permit"
    ],
    key="document_type"
)

uploaded_file = st.file_uploader(
    f"Upload {document_type} image",
    type=["jpg", "jpeg", "png"],
    key="document_upload"
)


# =========================================================
# PROCESS UPLOADED DOCUMENT
# =========================================================

if uploaded_file is not None:

    # -----------------------------------------------------
    # Open Image
    # -----------------------------------------------------

    image = Image.open(uploaded_file).convert("RGB")

    st.image(
        image,
        caption=f"Uploaded {document_type}",
        width=500
    )


    # =====================================================
    # CURRENT PROTOTYPE LIMITATION
    # =====================================================

    if document_type != "Passport":

        st.warning(
            f"⚠️ {document_type} is currently available in the UI, "
            "but the complete OCR/database verification pipeline "
            "in this prototype is implemented for Passport documents."
        )

        st.info(
            "The architecture can be extended to Visa, National ID, "
            "Driving License and Permit documents."
        )

        st.stop()


    # =====================================================
    # OCR
    # =====================================================

    st.write("### 🔍 OCR Extracted Text")

    try:
        text = pytesseract.image_to_string(image)
    except Exception as e:
        st.error(f"OCR error: {e}")
        st.stop()

    st.text(text)

    text_upper = text.upper()


    # =====================================================
    # FIND PASSPORT NUMBER
    # =====================================================

    st.write("### 🛂 Detected Passport Number")

    match = re.search(
        r'P\s*\d{4,6}',
        text_upper
    )

    if not match:

        st.warning(
            "⚠️ Passport number could not be detected."
        )

        st.info(
            "Make sure the passport number is clearly visible "
            "in the uploaded image."
        )

        st.stop()


    detected_no = match.group().replace(" ", "")

    st.success(detected_no)


    # =====================================================
    # FIND CLOSEST PASSPORT NUMBER
    # =====================================================

    best_match = None
    best_score = 0

    for db_no in data["passport_no"]:

        score = SequenceMatcher(
            None,
            detected_no,
            str(db_no).upper()
        ).ratio()

        if score > best_score:
            best_score = score
            best_match = db_no


    # =====================================================
    # DATABASE MATCH
    # =====================================================

    if best_match is None or best_score < 0.75:

        st.error(
            "❌ No matching passport record found in dataset."
        )

        st.write(
            f"Best matching score: {best_score:.2f}"
        )

        st.stop()


    record = data[
        data["passport_no"] == best_match
    ].iloc[0]


    st.info(
        f"Database record selected: {best_match}"
    )


    # =====================================================
    # OCR FIELD EXTRACTION
    # =====================================================

    name_match = re.search(
        r'NAME\s*:\s*([A-Z ]+)',
        text_upper
    )

    dob_match = re.search(
        r'DATE OF BIRTH\s*:\s*(\d{2}-\d{2}-\d{4})',
        text_upper
    )

    nationality_match = re.search(
        r'NATIONALITY\s*:\s*([A-Z]+)',
        text_upper
    )

    expiry_match = re.search(
        r'DATE OF EXPIRY\s*:\s*(\d{2}-\d{2}-\d{4})',
        text_upper
    )


    extracted_name = (
        name_match.group(1).strip()
        if name_match
        else ""
    )

    extracted_dob = (
        dob_match.group(1)
        if dob_match
        else ""
    )

    extracted_nationality = (
        nationality_match.group(1).strip()
        if nationality_match
        else ""
    )

    extracted_expiry = (
        expiry_match.group(1)
        if expiry_match
        else ""
    )


    # =====================================================
    # VERIFICATION DETAILS
    # =====================================================

    st.write("### 📋 Verification Details")

    comparison = pd.DataFrame({

        "Field": [
            "Name",
            "Date of Birth",
            "Nationality",
            "Date of Expiry"
        ],

        "OCR Value": [
            extracted_name,
            extracted_dob,
            extracted_nationality,
            extracted_expiry
        ],

        "Database Value": [
            record["name"],
            record["dob"],
            record["nationality"],
            record["expiry"]
        ]
    })


    st.dataframe(
        comparison,
        use_container_width=True
    )


    # =====================================================
    # FIELD COMPARISON
    # =====================================================

    name_ok = (
        extracted_name.upper().strip()
        == str(record["name"]).upper().strip()
    )

    dob_ok = (
        extracted_dob
        == str(record["dob"])
    )

    nationality_ok = (
        extracted_nationality.upper().strip()
        == str(record["nationality"]).upper().strip()
    )

    expiry_ok = (
        extracted_expiry
        == str(record["expiry"])
    )


    matches = sum([
        name_ok,
        dob_ok,
        nationality_ok,
        expiry_ok
    ])


    # =====================================================
    # EXPIRY VALIDATION
    # =====================================================

    st.write("### 📅 Expiry Validation")

    expired = False

    if extracted_expiry:

        try:

            expiry_date = datetime.strptime(
                extracted_expiry,
                "%d-%m-%Y"
            ).date()

            today = datetime.today().date()

            if expiry_date < today:

                expired = True

                st.error(
                    f"❌ Document expired on {expiry_date}"
                )

            else:

                st.success(
                    f"✅ Document is valid until {expiry_date}"
                )

        except ValueError:

            st.warning(
                "⚠️ Could not validate expiry date format."
            )

    else:

        st.warning(
            "⚠️ Expiry date could not be extracted."
        )


    # =====================================================
    # BLACKLIST / WATCHLIST CHECK
    # =====================================================

    st.write("### 🚨 Blacklist / Watchlist Check")

    blacklisted = False

    # Demo blacklist
    demo_blacklist = [
        "P99999"
    ]

    if str(best_match).upper() in demo_blacklist:

        blacklisted = True

    # Check dataset columns if available

    possible_columns = [
        "status",
        "blacklisted",
        "blacklist",
        "watchlist"
    ]

    for column in possible_columns:

        if column in data.columns:

            value = str(record[column]).lower().strip()

            if value in [
                "blacklisted",
                "true",
                "yes",
                "watchlist",
                "blocked"
            ]:

                blacklisted = True


    if blacklisted:

        st.error(
            "❌ Document/person appears in blacklist or watchlist."
        )

    else:

        st.success(
            "✅ No blacklist/watchlist match detected."
        )


    # =====================================================
    # MULTIPLE IDENTITY CHECK
    # =====================================================

    st.write("### 👥 Multiple Identity Check")

    multiple_identity = False

    same_name_records = data[
        data["name"].astype(str).str.upper().str.strip()
        == str(record["name"]).upper().strip()
    ]

    if len(same_name_records) > 1:

        multiple_identity = True

        st.warning(
            "⚠️ Multiple records found with the same name."
        )

        st.dataframe(
            same_name_records,
            use_container_width=True
        )

    else:

        st.success(
            "✅ No multiple identity record detected."
        )


    # =====================================================
    # FIELD CHECK RESULTS
    # =====================================================

    st.write("### 🔎 Field Checks")

    st.write(
        f"{'✅' if name_ok else '❌'} Name"
    )

    st.write(
        f"{'✅' if dob_ok else '❌'} Date of Birth"
    )

    st.write(
        f"{'✅' if nationality_ok else '❌'} Nationality"
    )

    st.write(
        f"{'✅' if expiry_ok else '❌'} Date of Expiry"
    )


    # =====================================================
    # TAMPER DETECTION
    # =====================================================

    st.write("### 🛡️ Tamper Detection")

    original_path = f"originals/{best_match}.png"

    change_percentage = 0.0

    tamper_detected = False

    if os.path.exists(original_path):

        original_image = cv2.imread(
            original_path
        )

        uploaded_cv = cv2.cvtColor(
            np.array(image),
            cv2.COLOR_RGB2BGR
        )

        if original_image is not None:

            uploaded_cv = cv2.resize(
                uploaded_cv,
                (
                    original_image.shape[1],
                    original_image.shape[0]
                )
            )

            difference = cv2.absdiff(
                original_image,
                uploaded_cv
            )

            gray_diff = cv2.cvtColor(
                difference,
                cv2.COLOR_BGR2GRAY
            )

            changed_pixels = cv2.countNonZero(
                gray_diff
            )

            total_pixels = (
                gray_diff.shape[0]
                * gray_diff.shape[1]
            )

            change_percentage = (
                changed_pixels
                / total_pixels
            ) * 100


            st.write(
                f"Image Difference: "
                f"**{change_percentage:.2f}%**"
            )


            if change_percentage < 2:

                st.success(
                    "✅ No significant image change detected."
                )

            else:

                tamper_detected = True

                st.warning(
                    "⚠️ Possible image tampering detected."
                )

        else:

            st.warning(
                "⚠️ Original reference image could not be read."
            )

    else:

        st.info(
            f"Original mock passport image not available: "
            f"{original_path}"
        )


    # =====================================================
    # FACE VERIFICATION
    # =====================================================

    st.write("### 👤 Face Verification")

    st.info(
        "Upload a reference face image for prototype face comparison."
    )

    face_file = st.file_uploader(
        "Upload reference face image",
        type=["jpg", "jpeg", "png"],
        key="reference_face"
    )

    face_status = "⚠️ FACE NOT CHECKED"

    face_similarity = 0.0

    if face_file is not None:

        # ---------------------------------------------
        # Read passport image
        # ---------------------------------------------

        passport_bytes = uploaded_file.getvalue()

        passport_array = np.frombuffer(
            passport_bytes,
            np.uint8
        )

        passport_img = cv2.imdecode(
            passport_array,
            cv2.IMREAD_GRAYSCALE
        )


        # ---------------------------------------------
        # Read reference face
        # ---------------------------------------------

        face_bytes = face_file.getvalue()

        face_array = np.frombuffer(
            face_bytes,
            np.uint8
        )

        reference_face = cv2.imdecode(
            face_array,
            cv2.IMREAD_GRAYSCALE
        )


        if (
            passport_img is not None
            and reference_face is not None
        ):

            # Resize both images
            passport_img = cv2.resize(
                passport_img,
                (200, 200)
            )

            reference_face = cv2.resize(
                reference_face,
                (200, 200)
            )


            # Compare image content
            difference = cv2.absdiff(
                passport_img,
                reference_face
            )

            mean_difference = np.mean(
                difference
            )

            face_similarity = max(
                0,
                100 - mean_difference
            )


            st.write(
                f"Face Similarity: "
                f"**{face_similarity:.2f}%**"
            )


            if face_similarity >= 60:

                face_status = "✅ FACE MATCH"

                st.success(
                    "✅ Face Match"
                )

            else:

                face_status = "❌ FACE MISMATCH"

                st.error(
                    "❌ Face Mismatch"
                )

        else:

            st.warning(
                "⚠️ Unable to process the uploaded images."
            )

    else:

        st.info(
            "Reference face image not uploaded."
        )

    st.write(
        f"Face Verification Result: **{face_status}**"
    )


    # =====================================================
    # RISK SCORE
    # =====================================================

    st.write("### ⚠️ Risk Assessment")

    # Base risk from field mismatches

    risk_score = (4 - matches) * 20


    # Expired document

    if expired:

        risk_score += 20


    # Tampering

    if tamper_detected:

        risk_score += 20


    # Blacklist

    if blacklisted:

        risk_score += 30


    # Multiple identities

    if multiple_identity:

        risk_score += 10


    # Face mismatch

    if face_status == "❌ FACE MISMATCH":

        risk_score += 20


    # Limit score to 100

    risk_score = min(
        risk_score,
        100
    )


    # =====================================================
    # RISK LEVEL
    # =====================================================

    if risk_score <= 20:

        risk_level = "LOW RISK"

    elif risk_score <= 40:

        risk_level = "MEDIUM RISK"

    elif risk_score <= 70:

        risk_level = "HIGH RISK"

    else:

        risk_level = "CRITICAL RISK"


    st.metric(
        "Risk Score",
        f"{risk_score}/100"
    )

    st.write(
        f"**Risk Level:** {risk_level}"
    )


    # =====================================================
    # VERIFICATION RESULT
    # =====================================================

    st.write("### 🎯 Verification Result")


    if (
        matches == 4
        and not expired
        and not tamper_detected
        and not blacklisted
        and not multiple_identity
        and face_status != "❌ FACE MISMATCH"
    ):

        result = "✅ VERIFIED"

        st.success(result)

    elif risk_score >= 70:

        result = "❌ HIGH RISK"

        st.error(result)

    else:

        result = "⚠️ REVIEW REQUIRED"

        st.warning(result)


    # =====================================================
    # VERIFICATION REASONS
    # =====================================================

    st.write("### 🔎 Verification Reasons")


    if not name_ok:

        st.write("❌ Name mismatch")


    if not dob_ok:

        st.write("❌ Date of Birth mismatch")


    if not nationality_ok:

        st.write("❌ Nationality mismatch")


    if not expiry_ok:

        st.write("❌ Date of Expiry mismatch")


    if expired:

        st.write("❌ Document is expired")


    if tamper_detected:

        st.write("⚠️ Possible document tampering detected")


    if blacklisted:

        st.write("❌ Blacklist/watchlist match detected")


    if multiple_identity:

        st.write("⚠️ Multiple identity records detected")


    if face_status == "❌ FACE MISMATCH":

        st.write("❌ Face verification failed")


    if (
        matches == 4
        and not expired
        and not tamper_detected
        and not blacklisted
        and not multiple_identity
        and face_status != "❌ FACE MISMATCH"
    ):

        st.write(
            "✅ All available verification checks passed."
        )


    # =====================================================
    # FINAL VERIFICATION SUMMARY
    # =====================================================

    st.write(
        "### 🔐 Final Verification Summary"
    )


    if result == "✅ VERIFIED":

        final_status = "✅ VERIFIED"

        st.success(final_status)

    elif risk_score >= 70:

        final_status = "❌ HIGH RISK"

        st.error(final_status)

    else:

        final_status = "⚠️ REVIEW REQUIRED"

        st.warning(final_status)


    # =====================================================
    # FINAL INFORMATION
    # =====================================================

    st.write(
        f"**Document Type:** {document_type}"
    )

    st.write(
        f"**Passport:** {best_match}"
    )

    st.write(
        f"**Field Verification:** {result}"
    )

    st.write(
        f"**Risk Score:** {risk_score}/100"
    )

    st.write(
        f"**Risk Level:** {risk_level}"
    )

    st.write(
        f"**Image Difference:** "
        f"{change_percentage:.2f}%"
    )

    st.write(
        f"**Face Verification:** {face_status}"
    )

    st.write(
        f"**Final Status:** {final_status}"
    )


    # =====================================================
    # VERIFICATION HISTORY
    # =====================================================

    if "verification_history" not in st.session_state:

        st.session_state.verification_history = []


    history_record = {

        "Passport": str(best_match),

        "Risk Score": risk_score,

        "Risk Level": risk_level,

        "Face": face_status,

        "Tampering": (
            "Detected"
            if tamper_detected
            else "Not Detected"
        ),

        "Final Status": final_status
    }


    st.session_state.verification_history.append(
        history_record
    )


    # =====================================================
    # VERIFICATION HISTORY DISPLAY
    # =====================================================

    st.write("### 📜 Verification History")

    if st.session_state.verification_history:

        history_df = pd.DataFrame(
            st.session_state.verification_history
        )

        st.dataframe(
            history_df,
            use_container_width=True
        )


    # =====================================================
    # WORKFLOW
    # =====================================================

    st.write("### 🔄 Screening Workflow")

    st.write(
        "📄 Upload Document "
        "→ 🔍 OCR Extraction "
        "→ 📋 Field Validation "
        "→ 🛡️ Tamper Detection "
        "→ 👤 Face Verification "
        "→ 🚨 Blacklist Check "
        "→ 👥 Multiple Identity Check "
        "→ ⚠️ Risk Score "
        "→ 🎯 Final Decision"
    )