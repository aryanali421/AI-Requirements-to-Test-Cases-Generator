
import os
import io
import json
import re
import csv
import streamlit as st
import pandas as pd
from groq import Groq
from pypdf import PdfReader
from docx import Document

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="TestForge | QA Workspace",
    page_icon="⌘",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================================================
# DESIGN SYSTEM
# ==================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #0A0D12;
    --panel: #121720;
    --panel2: #171F2B;
    --border: #263140;
    --text: #E7EBF2;
    --muted: #8995A6;
    --gold: #FFC233;
    --green: #86D6B0;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    max-width: 1350px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

#MainMenu, footer {
    visibility: hidden;
}

.brand {
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    letter-spacing: 2px;
    color: var(--gold);
    font-weight: 500;
}

.hero-title {
    font-size: clamp(34px, 5vw, 55px);
    font-weight: 800;
    letter-spacing: -2px;
    line-height: 1.1;
    margin-top: 25px;
    margin-bottom: 12px;
}

.hero-sub {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.7;
    max-width: 680px;
}

.step-label {
    color: var(--gold);
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    letter-spacing: 1.5px;
    margin-bottom: 10px;
}

.section-heading {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 5px;
}

.section-caption {
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 18px;
}

.panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 22px;
}

div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    background: #0D131C !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 9px !important;
    font-family: 'DM Sans', sans-serif !important;
}

div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stTextInput"] input:focus {
    border-color: var(--gold) !important;
    box-shadow: 0 0 0 1px var(--gold) !important;
}

div[data-testid="stSelectbox"] > div > div {
    background: #0D131C;
    border-color: var(--border);
    border-radius: 9px;
}

.stButton > button {
    background: var(--gold) !important;
    color: #151515 !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 800 !important;
    padding: 11px 20px !important;
    transition: all .2s ease;
}

.stButton > button:hover {
    background: #FFD36A !important;
    transform: translateY(-2px);
}

.stDownloadButton > button {
    background: var(--panel2) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 9px !important;
}

div[data-testid="stFileUploader"] {
    background: #0D131C;
    border: 1px dashed #38475A;
    border-radius: 10px;
    padding: 12px;
}

div[data-testid="stAlert"] {
    border-radius: 10px;
}

div[data-testid="stDataFrame"],
div[data-testid="stDataEditor"] {
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
}

[data-testid="stMetric"] {
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 17px;
    border-radius: 12px;
}

[data-testid="stMetricLabel"] {
    color: var(--muted);
}

[data-testid="stMetricValue"] {
    color: var(--gold);
}

div[data-testid="stExpander"] {
    border-color: var(--border);
    border-radius: 10px;
}

hr {
    border-color: var(--border);
    margin-top: 28px;
    margin-bottom: 28px;
}

.small-note {
    color: var(--muted);
    font-size: 12px;
}

[data-testid="stMarkdownContainer"] {
    color: var(--text);
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# SESSION STATE
# ==================================================

if "test_cases" not in st.session_state:
    st.session_state.test_cases = []

if "coverage_report" not in st.session_state:
    st.session_state.coverage_report = {}

if "generation_summary" not in st.session_state:
    st.session_state.generation_summary = ""


# ==================================================
# GROQ CONFIGURATION
# ==================================================

def get_api_key():
    key = os.getenv("GROQ_API_KEY")

    if not key:
        try:
            key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            key = None

    return key


# ==================================================
# DOCUMENT EXTRACTION
# ==================================================

def extract_document(uploaded_file):

    if uploaded_file is None:
        return ""

    filename = uploaded_file.name.lower()
    content = uploaded_file.getvalue()

    try:

        if filename.endswith(".txt"):
            return content.decode("utf-8", errors="replace")

        elif filename.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(content))

            return "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        elif filename.endswith(".docx"):
            doc = Document(io.BytesIO(content))

            return "\n".join(
                paragraph.text
                for paragraph in doc.paragraphs
                if paragraph.text.strip()
            )

    except Exception as error:
        st.error(f"Document extraction failed: {error}")

    return ""


# ==================================================
# JSON EXTRACTION
# ==================================================

def parse_json_response(response_text):

    cleaned = response_text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1:
        return json.loads(cleaned[start:end + 1])

    raise ValueError(
        "The model returned an invalid response. Please try again."
    )


# ==================================================
# TEST CASE GENERATION
# ==================================================

def generate_test_cases(
    requirements,
    project_name,
    application_type,
    test_types,
    detail_level,
    platform,
    additional_instructions
):

    api_key = get_api_key()

    if not api_key:
        raise ValueError(
            "Groq API key not found. Configure GROQ_API_KEY in secrets."
        )

    client = Groq(api_key=api_key)

    system_prompt = """
You are a senior software quality assurance engineer.

Your task is to analyze software requirements and generate
high-quality, practical and traceable software test cases.

You must:

1. Understand the actual functional requirements.
2. Generate test cases that directly relate to the requirements.
3. Include normal, boundary and invalid-input scenarios
   when requested.
4. Avoid duplicate or meaningless test cases.
5. Make each test case independently executable.
6. Provide clear preconditions and numbered test steps.
7. Write specific expected outcomes that can be verified.
8. Never invent functionality that the requirements do not specify.
9. Highlight ambiguity rather than silently assuming behavior.
10. Use realistic input examples.
11. Consider empty values, missing fields, incorrect formats,
    limits and unusual user behavior where relevant.
12. Distinguish between severity and execution priority.
13. Keep the output valid JSON.
14. Do not wrap the JSON in Markdown code fences.

A good test case must be actionable and testable,
not merely a vague description.
"""

    user_prompt = f"""
PROJECT INFORMATION

Project: {project_name}
Application type: {application_type}
Target platform: {platform}
Detail level: {detail_level}

SOFTWARE REQUIREMENTS:

{requirements}

REQUESTED TEST TYPES:

{", ".join(test_types)}

ADDITIONAL INSTRUCTIONS:

{additional_instructions or "No additional instructions."}

Generate a comprehensive set of relevant test cases.

Return a JSON object using EXACTLY this structure:

{{
    "summary": "Short summary of the analysis",
    "coverage": [
        {{
            "requirement": "Requirement name or description",
            "status": "Covered / Partially Covered / Not Covered",
            "notes": "Explanation of coverage"
        }}
    ],
    "test_cases": [
        {{
            "id": "TC-001",
            "requirement": "Related requirement",
            "title": "Short descriptive test title",
            "test_type": "Normal / Boundary / Invalid Input",
            "preconditions": "Conditions before execution",
            "test_steps": [
                "Step 1",
                "Step 2",
                "Step 3"
            ],
            "test_data": "Input values used",
            "expected_result": "Specific expected system behavior",
            "priority": "High / Medium / Low",
            "severity": "Critical / Major / Minor"
        }}
    ],
    "ambiguities": [
        "Requirement details that need clarification"
    ]
}}

IMPORTANT:

- Generate a minimum of 2 useful test cases per requested
  test category when the requirements provide enough information.
- Do not force a test case if the requirements do not support it.
- Do not fabricate requirements.
- Include relevant requirement references.
- Use sequential test IDs starting from TC-001.
- Ensure boundary cases test values immediately around
  specified limits whenever possible.
- Ensure invalid-input cases explain why the input is invalid.
- Expected results must be observable and verifiable.
- If a requirement does not define an expected behavior,
  flag that ambiguity.
- Return valid JSON only.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=7000,
        response_format={"type": "json_object"}
    )

    return parse_json_response(
        response.choices[0].message.content
    )


# ==================================================
# DATA VALIDATION
# ==================================================

def validate_test_cases(data):

    if not isinstance(data, dict):
        raise ValueError("Invalid response structure.")

    cases = data.get("test_cases")

    if not isinstance(cases, list) or not cases:
        raise ValueError("No test cases were generated.")

    validated = []

    for index, case in enumerate(cases, start=1):

        if not isinstance(case, dict):
            continue

        steps = case.get("test_steps", [])

        if isinstance(steps, str):
            steps = [steps]

        validated.append({
            "ID": str(case.get("id", f"TC-{index:03d}")),
            "Requirement": str(case.get("requirement", "")),
            "Title": str(case.get("title", "")),
            "Type": str(case.get("test_type", "")),
            "Preconditions": str(case.get("preconditions", "")),
            "Test Steps": "\n".join(
                str(step) for step in steps
            ),
            "Test Data": str(case.get("test_data", "")),
            "Expected Result": str(case.get("expected_result", "")),
            "Priority": str(case.get("priority", "Medium")),
            "Severity": str(case.get("severity", "Minor"))
        })

    if not validated:
        raise ValueError("No valid test cases found.")

    return validated


# ==================================================
# CSV EXPORT
# ==================================================

def create_csv(dataframe):

    output = io.StringIO()

    dataframe.to_csv(
        output,
        index=False,
        quoting=csv.QUOTE_ALL,
        encoding="utf-8"
    )

    return "\ufeff" + output.getvalue()


# ==================================================
# HEADER
# ==================================================

st.markdown(
    '<div class="brand">⌘ TESTFORGE / QA WORKSPACE</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="hero-title">Turn requirements into '
    '<span style="color:#FFC233">testable reality.</span></div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="hero-sub">'
    'Translate software requirements into structured test cases. '
    'Identify edge cases, validate expected behavior and build '
    'a more reliable testing foundation.'
    '</div>',
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)


# ==================================================
# PROJECT INFORMATION
# ==================================================

st.markdown(
    '<div class="step-label">01 / PROJECT CONFIGURATION</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-heading">Project details</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-caption">'
    'Define the application you are testing.'
    '</div>',
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)

with col1:
    project_name = st.text_input(
        "Project name",
        placeholder="e.g. Student Portal"
    )

with col2:
    application_type = st.selectbox(
        "Application type",
        [
            "Web application",
            "Mobile application",
            "Desktop application",
            "API / Backend",
            "E-commerce platform",
            "Other"
        ]
    )

with col3:
    platform = st.selectbox(
        "Target environment",
        [
            "Cross-platform",
            "Windows",
            "macOS",
            "Linux",
            "Android",
            "iOS",
            "Browser / Web"
        ]
    )

st.markdown("<br>", unsafe_allow_html=True)


# ==================================================
# REQUIREMENTS INPUT
# ==================================================

st.markdown(
    '<div class="step-label">02 / REQUIREMENTS ANALYSIS</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-heading">Software requirements</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-caption">'
    'Paste your functional and non-functional requirements '
    'or upload an existing specification.'
    '</div>',
    unsafe_allow_html=True
)

input_col, upload_col = st.columns([1.2, 0.8], gap="large")

with input_col:

    requirements_text = st.text_area(
        "Requirements",
        placeholder="""Example:

REQ-001: User Registration

The system shall allow users to create an account
using their email address and password.

REQ-002: Password Validation

Passwords must contain at least 8 characters,
including one uppercase letter and one number.

REQ-003: Login

Registered users shall be able to log in using
their email and password.

REQ-004: Failed Login

After 5 consecutive failed login attempts,
the account shall be temporarily locked.""",
        height=270
    )

with upload_col:

    uploaded_file = st.file_uploader(
        "Upload requirements document",
        type=["pdf", "docx", "txt"],
        help="Supported: PDF, DOCX and TXT"
    )

    if uploaded_file:
        st.success(f"Attached: {uploaded_file.name}")

    st.markdown(
        '<p class="small-note">'
        'You can paste requirements, upload a document, '
        'or combine both.'
        '</p>',
        unsafe_allow_html=True
    )


# ==================================================
# TEST GENERATION SETTINGS
# ==================================================

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

st.markdown(
    '<div class="step-label">03 / GENERATION SETTINGS</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-heading">Choose your test coverage</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-caption">'
    'Select which scenarios the generator should explore.'
    '</div>',
    unsafe_allow_html=True
)

type_col, detail_col = st.columns([1.1, 0.9], gap="large")

with type_col:

    test_types = st.multiselect(
        "Test case categories",
        [
            "Normal",
            "Boundary",
            "Invalid Input"
        ],
        default=[
            "Normal",
            "Boundary",
            "Invalid Input"
        ],
        help="Choose one or more categories."
    )

    st.markdown(
        """
        <div class="panel">
            <div style="color:#FFC233;font-weight:700;">
                Normal testing
            </div>
            <p class="small-note">
                Verify expected behavior with valid inputs.
            </p>
            <div style="color:#FFC233;font-weight:700;">
                Boundary testing
            </div>
            <p class="small-note">
                Explore minimums, maximums and edge values.
            </p>
            <div style="color:#FFC233;font-weight:700;">
                Invalid-input testing
            </div>
            <p class="small-note">
                Check missing, malformed and unacceptable inputs.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with detail_col:

    detail_level = st.selectbox(
        "Generation depth",
        [
            "Balanced coverage",
            "Detailed coverage",
            "Comprehensive coverage"
        ],
        index=1
    )

    additional_instructions = st.text_area(
        "Additional instructions (optional)",
        placeholder="e.g. Focus on authentication, security "
                    "and input validation.",
        height=125
    )

    st.caption(
        "Generation depth influences the level of detail, "
        "not a guaranteed test-case count."
    )


# ==================================================
# GENERATE BUTTON
# ==================================================

st.markdown("<br>", unsafe_allow_html=True)

generate_col, note_col = st.columns([1, 1])

with generate_col:

    generate = st.button(
        "⌘  Generate test cases",
        use_container_width=True
    )

with note_col:

    st.markdown(
        '<p class="small-note" style="padding-top:12px">'
        'Requirements are analyzed by Groq. '
        'Generated test cases should be validated before execution.'
        '</p>',
        unsafe_allow_html=True
    )


# ==================================================
# GENERATION PROCESS
# ==================================================

if generate:

    extracted_text = ""

    if uploaded_file:

        if uploaded_file.size > 10 * 1024 * 1024:
            st.error("Please upload a file smaller than 10 MB.")
            st.stop()

        extracted_text = extract_document(uploaded_file)

    final_requirements = "\n\n".join(
        part for part in [
            requirements_text.strip(),
            extracted_text.strip()
        ] if part
    )

    if not final_requirements:
        st.error("Please enter or upload software requirements.")

    elif len(final_requirements) > 50000:
        st.error("Requirements exceed the 50,000 character limit.")

    elif not test_types:
        st.error("Please select at least one test category.")

    else:

        try:

            with st.spinner(
                "Analyzing requirements and designing test scenarios..."
            ):

                response = generate_test_cases(
                    requirements=final_requirements,
                    project_name=project_name or "Untitled Project",
                    application_type=application_type,
                    test_types=test_types,
                    detail_level=detail_level,
                    platform=platform,
                    additional_instructions=additional_instructions
                )

                validated_cases = validate_test_cases(response)

                st.session_state.test_cases = validated_cases

                st.session_state.coverage_report = {
                    "coverage": response.get("coverage", []),
                    "ambiguities": response.get("ambiguities", [])
                }

                st.session_state.generation_summary = response.get(
                    "summary",
                    "Test cases generated successfully."
                )

                st.success("Test cases generated successfully!")

        except Exception as error:
            st.error(f"Generation failed: {error}")


# ==================================================
# RESULTS WORKSPACE
# ==================================================

if st.session_state.test_cases:

    st.markdown("---")

    st.markdown(
        '<div class="step-label">04 / TEST MANAGEMENT</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-heading">Generated test cases</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-caption">'
        'Review, edit and export your generated test suite.'
        '</div>',
        unsafe_allow_html=True
    )

    cases = st.session_state.test_cases

    df = pd.DataFrame(cases)

    total = len(df)
    normal = int((df["Type"].str.lower() == "normal").sum())
    boundary = int((df["Type"].str.lower() == "boundary").sum())
    invalid = int(
        df["Type"].str.lower().isin(
            ["invalid", "invalid input"]
        ).sum()
    )

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric("Total test cases", total)
    metric2.metric("Normal", normal)
    metric3.metric("Boundary", boundary)
    metric4.metric("Invalid input", invalid)

    st.markdown("<br>", unsafe_allow_html=True)

    st.info(st.session_state.generation_summary)

    # --------------------------------------------------
    # EDITABLE TEST CASE TABLE
    # --------------------------------------------------

    st.markdown("### Test case register")

    st.caption(
        "Click any cell to edit its contents. "
        "Changes are used in the exported CSV."
    )

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="test_case_editor",
        column_config={
            "ID": st.column_config.TextColumn(
                "Test ID",
                disabled=True,
                width="small"
            ),
            "Requirement": st.column_config.TextColumn(
                "Requirement",
                width="medium"
            ),
            "Title": st.column_config.TextColumn(
                "Test case",
                width="large"
            ),
            "Type": st.column_config.SelectboxColumn(
                "Category",
                options=[
                    "Normal",
                    "Boundary",
                    "Invalid Input"
                ]
            ),
            "Preconditions": st.column_config.TextColumn(
                "Preconditions",
                width="medium"
            ),
            "Test Steps": st.column_config.TextColumn(
                "Test steps",
                width="large"
            ),
            "Test Data": st.column_config.TextColumn(
                "Test data",
                width="medium"
            ),
            "Expected Result": st.column_config.TextColumn(
                "Expected result",
                width="large"
            ),
            "Priority": st.column_config.SelectboxColumn(
                "Priority",
                options=["High", "Medium", "Low"]
            ),
            "Severity": st.column_config.SelectboxColumn(
                "Severity",
                options=["Critical", "Major", "Minor"]
            )
        }
    )

    # Save edited version for downloads
    st.session_state.test_cases = edited_df.to_dict("records")

    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------
    # INDIVIDUAL TEST CASE DETAILS
    # --------------------------------------------------

    with st.expander("View individual test case details"):

        for _, case in edited_df.iterrows():

            with st.container():

                st.markdown(
                    f"**{case['ID']} · {case['Title']}**"
                )

                st.caption(
                    f"{case['Type']}  |  "
                    f"Priority: {case['Priority']}  |  "
                    f"Severity: {case['Severity']}"
                )

                st.markdown(
                    f"**Requirement:** {case['Requirement']}"
                )

                st.markdown(
                    f"**Preconditions:** {case['Preconditions']}"
                )

                st.markdown("**Test steps:**")

                st.markdown(str(case["Test Steps"]))

                st.markdown(
                    f"**Test data:** {case['Test Data']}"
                )

                st.markdown(
                    f"**Expected result:** {case['Expected Result']}"
                )

                st.markdown("---")

    # --------------------------------------------------
    # COVERAGE ANALYSIS
    # --------------------------------------------------

    st.markdown("### Requirement coverage")

    coverage = st.session_state.coverage_report.get(
        "coverage", []
    )

    if coverage:

        coverage_df = pd.DataFrame(coverage)

        st.dataframe(
            coverage_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.caption("No coverage details were returned.")

    # --------------------------------------------------
    # AMBIGUITIES
    # --------------------------------------------------

    ambiguities = st.session_state.coverage_report.get(
        "ambiguities", []
    )

    with st.expander(
        f"Requirement ambiguities ({len(ambiguities)})"
    ):

        if ambiguities:

            for item in ambiguities:
                st.markdown(f"- {item}")

        else:
            st.success("No ambiguities were identified.")

    # --------------------------------------------------
    # EXPORT
    # --------------------------------------------------

    st.markdown("---")

    st.markdown(
        '<div class="step-label">05 / EXPORT</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-heading">Take your test suite with you</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-caption">'
        'Export your reviewed test cases for documentation and execution.'
        '</div>',
        unsafe_allow_html=True
    )

    export_col, reset_col = st.columns([1, 1])

    with export_col:

        csv_data = create_csv(edited_df)

        st.download_button(
            "↓  Download test cases (CSV)",
            data=csv_data,
            file_name="testforge_test_cases.csv",
            mime="text/csv",
            use_container_width=True
        )

    with reset_col:

        if st.button(
            "Clear test suite",
            use_container_width=True
        ):

            st.session_state.test_cases = []
            st.session_state.coverage_report = {}
            st.session_state.generation_summary = ""

            if "test_case_editor" in st.session_state:
                del st.session_state["test_case_editor"]

            st.rerun()


# ==================================================
# FOOTER
# ==================================================

st.markdown("---")

st.markdown(
    """
    <div style="text-align:center;padding:15px 0;">
        <div class="brand">⌘ TESTFORGE</div>
        <p class="small-note">
            From requirements to reliable testing.
            <br><br>
            AI-assisted QA · Human-validated test cases
        </p>
    </div>
    """,
    unsafe_allow_html=True
)



