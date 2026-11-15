import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import time
import random

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Monitor system",
    page_icon="👾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- LANGUAGE SELECTION (default: English) ---
LANGUAGES = ["English", "Ελληνικά"]
lang = st.sidebar.selectbox("🌎 Language / Γλώσσα", LANGUAGES, index=0)
IS_EL = lang == "Ελληνικά"


def T(en, el):
    """Return the text in the selected language."""
    return el if IS_EL else en


# --- CUSTOM CSS FOR SPACE DARK UI ---
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    .metric-card {
        background-color: #131b2e;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .alert-tier1 { background-color: #1e3a8a; border-left: 5px solid #3b82f6; padding: 12px; border-radius: 6px; margin-bottom: 10px; }
    .alert-tier2 { background-color: #78350f; border-left: 5px solid #f59e0b; padding: 12px; border-radius: 6px; margin-bottom: 10px; }
    .alert-tier3 { background-color: #7f1d1d; border-left: 5px solid #ef4444; padding: 12px; border-radius: 6px; margin-bottom: 10px; }
    .alert-nominal { background-color: #064e3b; border-left: 5px solid #10b981; padding: 12px; border-radius: 6px; margin-bottom: 10px; }
    .phase-box { background-color: #131b2e; border: 1px solid #38bdf8; border-radius: 8px; padding: 14px; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZATION OF SESSION STATE ---
if "preset" not in st.session_state:
    st.session_state.preset = "Nominal"
if "pvt_state" not in st.session_state:
    st.session_state.pvt_state = "IDLE"
if "pvt_start_time" not in st.session_state:
    st.session_state.pvt_start_time = 0.0
if "pvt_results" not in st.session_state:
    st.session_state.pvt_results = [0, 0, 0]
if "xp" not in st.session_state:
    st.session_state.xp = 420
if "streak" not in st.session_state:
    st.session_state.streak = 14

# --- PREDEFINED DEMO SCENARIOS ---
PRESETS = {
    "Nominal": {
        "mission_day": 35, "env": "ISS / Lunar Gateway", "sex": "Female",
        "hrv": 58, "spo2": 98, "bp_sys": 118, "bp_dia": 76, "glucose": 92, "temp": 36.7, "siga": 145,
        "sleep_h": 7.8, "sleep_lat": 12, "vas_energy": 85, "vas_mood": 88, "vas_stress": 22, "vas_social": 90,
        "pvt_rt": 0, "pvt_lapses": 0, "voice_f0": "Stable (210 Hz)", "voice_pause": 12, "duration_days": 1
    },
    "Cumulative Isolation Stress": {
        "mission_day": 165, "env": "Mars Transit (520d)", "sex": "Male",
        "hrv": 24, "spo2": 96, "bp_sys": 134, "bp_dia": 86, "glucose": 114, "temp": 36.9, "siga": 85,
        "sleep_h": 5.2, "sleep_lat": 38, "vas_energy": 45, "vas_mood": 42, "vas_stress": 76, "vas_social": 35,
        "pvt_rt": 310, "pvt_lapses": 2, "voice_f0": "Flattened (-18%)", "voice_pause": 32, "duration_days": 5
    },
    "Acute Deprivation / CO2 Pocket": {
        "mission_day": 210, "env": "Artemis Lunar Base", "sex": "Male",
        "hrv": 19, "spo2": 91, "bp_sys": 142, "bp_dia": 92, "glucose": 128, "temp": 37.1, "siga": 65,
        "sleep_h": 3.8, "sleep_lat": 45, "vas_energy": 25, "vas_mood": 30, "vas_stress": 88, "vas_social": 25,
        "pvt_rt": 435, "pvt_lapses": 4, "voice_f0": "High Jitter / Monotone", "voice_pause": 41, "duration_days": 8
    }
}

# --- SIDEBAR: MISSION TELEMETRY & DEMO CONTROLS ---
with st.sidebar:
    st.title("👽 C.O.R.E. ")
    st.caption("NASA HRP / BHP Integrated Telemetry")

    st.subheader("Pitch-Ready Demo Scenarios")
    col_p1, col_p2, col_p3 = st.columns(3)
    if col_p1.button("A: Nominal"):
        st.session_state.preset = "Nominal"
        st.session_state.pvt_results = [0, 0, 0]
    if col_p2.button("B: Stress"):
        st.session_state.preset = "Cumulative Isolation Stress"
        st.session_state.pvt_results = [305, 318, 307]
    if col_p3.button("C: Critical"):
        st.session_state.preset = "Acute Deprivation / CO2 Pocket"
        st.session_state.pvt_results = [410, 525, 540]

    p = PRESETS[st.session_state.preset]

    st.divider()
    st.subheader(T("Mission Parameters", "Παράμετροι Αποστολής"))
    env_list = ["ISS / Lunar Gateway", "Orion Spacecraft", "Artemis Lunar Base", "Mars Transit (520d)"]
    env = st.selectbox(T("Environment", "Περιβάλλον"), env_list, index=env_list.index(p["env"]))
    sex = st.radio(T("Biological Sex (Sex & Gender Adjustment)", "Βιολογικό Φύλο (Sex & Gender Adjustment)"),
                   ["Male", "Female"], index=0 if p["sex"] == "Male" else 1, horizontal=True)
    mission_day = st.slider(T("Mission Day (1 - 270)", "Ημέρα Αποστολής (1 - 270)"), 1, 270, p["mission_day"])

    # Determination of Psychobiological Phase & Immediate Solutions (8-9 Month Model)
    if mission_day <= 60:
        phase_name = T("Phase 1: Adaptation & Euphoria (Months 1–2)", "Φάση 1: Προσαρμογή & Ευφορία (Μήνες 1–2)")
        phase_hormones = T("Dopamine & Oxytocin: High | Cortisol: Controlled",
                           "Ντοπαμίνη & Ωκυτοκίνη: Υψηλές | Κορτιζόλη: Ελεγχόμενη")
        phase_risks = T("Overwork and fatigue, neglecting rest due to enthusiasm, rushing through protocols.",
                        "Υπερεργασία και κούραση, παράβλεψη ξεκούρασης λόγω ενθουσιασμού, βιασύνη σε πρωτόκολλα.")
        phase_solutions = [
            T("Regular sessions with ground-based psychologists.", "Τακτική συνομιλία με ειδικούς ψυχολόγους εδάφους."),
            T("Strict adherence to the sleep and break schedule.", "Αυστηρή τήρηση προγράμματος ύπνου και διαλείμματος."),
            T("Use of music and relaxation techniques.", "Χρήση μουσικής και τεχνικών χαλάρωσης.")
        ]
    elif mission_day <= 120:
        phase_name = T("Phase 2: Routine & Monotony (Months 3–4)", "Φάση 2: Ρουτίνα & Μονοτονία (Μήνες 3–4)")
        phase_hormones = T("Dopamine & Serotonin: Declining | Melatonin: Dysregulated",
                           "Ντοπαμίνη & Σεροτονίνη: Σε πτώση | Μελατονίνη: Απορρυθμισμένη")
        phase_risks = T("Slower task performance, careless errors, minor crew friction, brain fog.",
                        "Μείωση ταχύτητας εργασιών, λάθη απροσεξίας, μικροπροστριβές μεταξύ πληρώματος, brain fog.")
        phase_solutions = [
            T("Rotation of roles and duties to prevent boredom.", "Εναλλαγή ρόλων και καθηκόντων για αποφυγή πλήξης."),
            T("Exposure to novel stimuli (surprise items in supplies, games).", "Έκθεση σε νέα ερεθίσματα (έκπληξη σε προμήθειες, παιχνίδια)."),
            T("Adjustment of dynamic LED lighting on the station.", "Ρύθμιση δυναμικού φωτισμού LED στο σταθμό.")
        ]
    elif mission_day <= 210:
        phase_name = T("Phase 3: Third-Quarter Crisis (Months 5–7)", "Φάση 3: Κρίση 3ου Τετάρτου (Μήνες 5–7)")
        phase_hormones = T("Cortisol: Persistently high | Dopamine & Serotonin: At their nadir",
                           "Κορτιζόλη: Μόνιμα υψηλή | Ντοπαμίνη & Σεροτονίνη: Στο ναδίρ")
        phase_risks = T("High risk of critical human error, communication breakdown with Mission Control, burnout, withdrawal.",
                        "Υψηλός κίνδυνος κρίσιμου ανθρώπινου λάθους, ρήξη επικοινωνίας με Κέντρο Ελέγχου, burnout, απόσυρση.")
        phase_solutions = [
            T("Mandatory technology-free crew meals.", "Υποχρεωτικά ομαδικά γεύματα χωρίς τεχνολογία."),
            T("Earth observation from the Cupola for uplift.", "Παρατήρηση της Γης από τον θόλο (Cupola) για ανάταση."),
            T("Intensive aerobic exercise and strength training (ARED).", "Εντατική αεροβική άσκηση και ενδυνάμωση (ARED).")
        ]
    else:
        phase_name = T("Phase 4: Final Stretch & Return (Months 8–9)", "Φάση 4: Τελική Ευθεία & Επιστροφή (Μήνες 8–9)")
        phase_hormones = T("Adrenaline: High | Dopamine: Partial recovery",
                           "Αδρεναλίνη: Υψηλή | Ντοπαμίνη: Μερική ανάκαμψη")
        phase_risks = T("Mental \"absence\" during close-out tasks, rushing and skipping safety checks, physical exhaustion.",
                        "Νοητική «απουσία» από εργασίες κλεισίματος, βιασύνη και παράλειψη δικλίδων ασφαλείας, σωματική εξάντληση.")
        phase_solutions = [
            T("Strict adherence to safety checklists.", "Αυστηρή τήρηση λιστών ελέγχου (checklists) ασφαλείας."),
            T("Re-entry preparation using approved protocols.", "Προετοιμασία επανεισόδου με εγκεκριμένα πρωτόκολλα."),
            T("Continuous communication with family and support.", "Συνεχής επικοινωνία με την οικογένεια και υποστήριξη.")
        ]

    st.info(f"**{phase_name}**\n\n🧬 *{phase_hormones}*\n\n⚠️ **{T('Risks', 'Κίνδυνοι')}:** {phase_risks}")
    st.markdown(T("**Immediate Phase Solutions:**", "**Άμεσες Λύσεις Φάσης:**"))
    for sol in phase_solutions:
        st.markdown(f"- {sol}")

    #st.divider()
    #st.metric("Resilience Streak & XP", f"{st.session_state.streak} {T('Days', 'Ημέρες')}", f"{st.session_state.xp} XP")

# --- MAIN APPLICATION AREA (3 INTEGRATED TABS) ---
st.title("👨‍🚀 Crew Operational Readiness Engine")
st.markdown(T(
    f"**Environment:** `{env}` | **Crew:** `ASTRO-01 ({sex})` | **Mission Day:** `{mission_day}/270` | **Status:** `{phase_name}`",
    f"**Περιβάλλον:** `{env}` | **Πλήρωμα:** `ASTRO-01 ({sex})` | **Mission Day:** `{mission_day}/270` | **Κατάσταση:** `{phase_name}`"
))

tabs = st.tabs([
    T(" 1. Biometrics, Body & Physiological Alerts (APP 1)", "🫀 1. Βιομετρία, Σώμα & Φυσιολογικά Alerts (APP 1)"),
    T(" 2. Neurocognition, Sleep & CRS Alerts (APP 2)", "🧠 2. Νευρογνωστικά, Ύπνος & CRS Alerts (APP 2)"),
    T(" 3. Strain Questionnaire (Q1–Q15) & Holistic Countermeasures", "📋 3. Ερωτηματολόγιο Επιβάρυνσης (Ε1–Ε15) & Ολιστικά Αντίμετρα")
])

# Preliminary PVT calculation so it is available in all Tabs for Crosstalk Alerts
pvt_mean = int(sum(st.session_state.pvt_results) / len(st.session_state.pvt_results))
pvt_lapses = sum(1 for x in st.session_state.pvt_results if x > 500)

# ==============================================================================
# TAB 1: BIOMETRICS, HUMAN BODY & PHYSIOLOGICAL / CROSSTALK ALERTS
# ==============================================================================
with tabs[0]:
    col_bio1, col_bio2 = st.columns([1.2, 1])

    with col_bio1:
        st.subheader(T("Physiological & Immunological Biomarkers", "Φυσιολογικοί & Ανοσολογικοί Βιοδείκτες"))
        c1, c2, c3 = st.columns(3)
        hrv = c1.number_input(T("Nocturnal HRV rMSSD (ms)", "Νυχτερινό HRV rMSSD (ms)"), 10, 120, p["hrv"])
        spo2 = c2.number_input(T("Nocturnal SpO₂ (%)", "Νυχτερινό SpO₂ (%)"), 85, 100, p["spo2"])
        glucose = c3.number_input(T("Fasting Glucose (mg/dL)", "Γλυκόζη Νηστείας (mg/dL)"), 60, 200, p["glucose"])

        c4, c5, c6 = st.columns(3)
        bp_sys = c4.number_input(T("Systolic Pressure (mmHg)", "Συστολική Πίεση (mmHg)"), 90, 180, p["bp_sys"])
        bp_dia = c5.number_input(T("Diastolic Pressure (mmHg)", "Διαστολική Πίεση (mmHg)"), 50, 120, p["bp_dia"])
        siga = c6.number_input(T("Salivary Secretory IgA (μg/mL)", "Εκκριτική IgA Σάλιου (μg/mL)"), 20, 250, p["siga"])

        st.markdown(T("### 🧬 Biosystem Selection & NASA Spaceflight Hazards",
                      "### 🧬 Επιλογή Βιοσυστήματος & NASA Spaceflight Hazards"))

        # Internal keys stay fixed; only the displayed labels change with the language
        ORGAN_LABELS = {
            "cns": T("Central Nervous System (CNS) & HPA Axis", "Κεντρικό Νευρικό Σύστημα (ΚΝΣ) & Άξονας HPA"),
            "immune": T("Immune System & Latent Viruses (EBV/CMV)", "Ανοσοποιητικό Σύστημα & Λανθάνοντες Ιοί (EBV/CMV)"),
            "cardio": T("Cardiovascular & Autonomic System (HRV)", "Καρδιαγγειακό Σύστημα & Αυτόνομο (HRV)"),
            "gut": T("Gut-Brain Axis & Metabolism", "Άξονας Εντέρου-Εγκεφάλου & Μεταβολισμός"),
            "msk": T("Musculoskeletal System & Bone Density", "Μυοσκελετικό Σύστημα & Οστική Πυκνότητα"),
        }
        organ = st.selectbox(T("Select a System for Self-Assessment & Guidance:",
                               "Επιλέξτε Σύστημα για Αυτο-Αξιολόγηση & Οδηγίες:"),
                             list(ORGAN_LABELS.keys()), format_func=lambda k: ORGAN_LABELS[k])

        organ_info = {
            "cns": ("Isolation, Radiation, Altered Gravity",
                    T("HPA axis hyperactivation, increased cortisol, reduced BDNF/serotonin and neuroinflammation.",
                      "Υπερδιέγερση άξονα HPA, αύξηση κορτιζόλης, πτώση BDNF/σεροτονίνης και νευροφλεγμονή."),
                    T("Earth observation from the Cupola, dynamic LED lighting adjustment and 15' VR Nature relaxation.",
                      "Παρατήρηση της Γης από τον θόλο (Cupola), ρύθμιση δυναμικού φωτισμού LED και 15' VR Nature relaxation.")),
            "immune": ("Radiation, Isolation, Circadian Disruption",
                       T("Suppression of CD8+ T-lymphocytes, rise in IL-6/TNF-α, drop in salivary sIgA and herpesvirus reactivation.",
                         "Καταστολή CD8+ Τ-λεμφοκυττάρων, άνοδος IL-6/TNF-α, πτώση sIgA σάλιου και επανενεργοποίηση ερπητοϊών."),
                       T("Saliva sampling (sIgA/viral DNA), strict adherence to the sleep schedule and mandatory crew meals.",
                         "Δειγματοληψία σάλιου (sIgA/viral DNA), αυστηρή τήρηση προγράμματος ύπνου και υποχρεωτικά ομαδικά γεύματα.")),
            "cardio": ("Altered Gravity, Hostile Closed Environment",
                       T("Loss of parasympathetic tone (rMSSD drop >20%) and increased vascular resistance.",
                         "Απώλεια παρασυμπαθητικού τόνου (πτώση rMSSD >20%) και αύξηση αγγειακής αντίστασης."),
                       T("Morning resting HRV recording, intensive aerobic exercise and strength training (ARED).",
                         "Καταγραφή πρωινού HRV ηρεμίας, εντατική αεροβική άσκηση και ενδυνάμωση (ARED).")),
            "gut": ("Closed Environment, Inadequate Nutrition",
                    T("Reduction of beneficial Bifidobacteria, insulin resistance (GLUT-4) and gastrointestinal discomfort.",
                      "Μείωση ωφέλιμων Bifidobacteria, αντίσταση στην ινσουλίνη (GLUT-4) και γαστρεντερική δυσφορία."),
                    T("Glucose measurement, technology-free crew meals, low glycemic index meal.",
                      "Μέτρηση γλυκόζης, ομαδικά γεύματα χωρίς τεχνολογία, γεύμα χαμηλού γλυκαιμικού δείκτη.")),
            "msk": ("Microgravity, Psychosocial Stress",
                    T("Osteoclast activation (calcium loss) and chronic neck/shoulder muscle tension.",
                      "Ενεργοποίηση οστεοκλαστών (απώλεια ασβεστίου) και χρόνια μυϊκή υπερένταση αυχένα/ώμων."),
                    T("Intensive aerobic exercise and strength training (ARED), relaxation techniques and stretching.",
                      "Εντατική αεροβική άσκηση και ενδυνάμωση (ARED), τεχνικές χαλάρωσης και διατάσεις.")),
        }
        hz, mech, action = organ_info[organ]
        st.info(T(
            f"**Primary NASA Hazards:** {hz}\n\n**Biological Mechanism:** {mech}\n\n**Immediate Countermeasure Protocol:** {action}",
            f"**Κύριοι Κίνδυνοι NASA:** {hz}\n\n**Βιολογικός Μηχανισμός:** {mech}\n\n**Άμεσο Πρωτόκολλο Αντιμέτρων:** {action}"
        ))

    with col_bio2:
        st.subheader(T("📊 Biosystem Status Map", "📊 Χάρτης Κατάστασης Βιοσυστημάτων"))
        cns_score = max(0, min(100, int(100 - (p["vas_stress"] * 0.6))))
        imm_score = max(0, min(100, int((siga / 150) * 100)))
        cv_score = max(0, min(100, int((hrv / 60) * 100)))
        met_score = max(0, min(100, int(100 - abs(glucose - 90) * 1.2)))

        fig_radar = go.Figure(data=go.Scatterpolar(
            r=[cns_score, imm_score, cv_score, met_score, 82],
            theta=[T('CNS / HPA', 'ΚΝΣ / HPA'), T('Immune', 'Ανοσοποιητικό'),
                   T('Cardiovascular (HRV)', 'Καρδιαγγειακό (HRV)'), T('Metabolism', 'Μεταβολισμός'),
                   T('Musculoskeletal', 'Μυοσκελετικό')],
            fill='toself',
            line_color='#38bdf8'
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100], gridcolor='#1e293b'), bgcolor='#131b2e'),
            paper_bgcolor='#0b0f19', font_color='#e2e8f0', height=360, margin=dict(t=30, b=30)
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # --- INTEGRATED BIOMETRIC & CROSSTALK ALERTS IN TAB 1 ---
    st.divider()
    st.subheader(T("Biometric & Environmental Alerts", "Βιομετρικά & Περιβαλλοντικά Alerts"))

    bio_alerts_triggered = False
    if spo2 < 93 and pvt_mean > 280:
        bio_alerts_triggered = True
        st.markdown(T("""
        <div class="alert-tier3">
            <h4> HABITAT CO₂ POCKET INDUCED COGNITIVE DEFICIT</h4>
            <p><b>Diagnosis:</b> Combination of nocturnal hypoxemia (SpO₂ < 93%) with PVT slowing (>280 ms). Indicates a CO₂ pocket accumulating in the sleep quarters.</p>
            <p><b>Immediate Solution:</b> Immediately check sleep quarters ventilation, increase ECLSS airflow and postpone critical maintenance tasks for 2 hours.</p>
        </div>
        """, """
        <div class="alert-tier3">
            <h4> HABITAT CO₂ POCKET INDUCED COGNITIVE DEFICIT</h4>
            <p><b>Διάγνωση:</b> Συνδυασμός νυχτερινής υποξαιμίας (SpO₂ < 93%) με επιβράδυνση PVT (>280 ms). Υποδεικνύει συσσώρευση θύλακα CO₂ στην καμπίνα ύπνου.</p>
            <p><b>Άμεση Λύση:</b> Ελέγξτε άμεσα τον εξαερισμό της καμπίνας ύπνου, αυξήστε τη ροή αέρα ECLSS και αναβάλετε κρίσιμες εργασίες συντήρησης για 2 ώρες.</p>
        </div>
        """), unsafe_allow_html=True)
    elif spo2 < 93:
        bio_alerts_triggered = True
        st.markdown(T("""
        <div class="alert-tier2">
            <h4> [TIER 2 BIOMETRIC ALERT] LOW NOCTURNAL OXYGEN SATURATION (SpO₂ < 93%)</h4>
            <p><b>Immediate Solution:</b> Check sleep quarters ventilation and repeat pulse oximetry at rest.</p>
        </div>
        """, """
        <div class="alert-tier2">
            <h4>[TIER 2 BIOMETRIC ALERT] ΧΑΜΗΛΟΣ ΝΥΧΤΕΡΙΝΟΣ ΚΟΡΕΣΜΟΣ ΟΞΥΓΟΝΟΥ (SpO₂ < 93%)</h4>
            <p><b>Άμεση Λύση:</b> Έλεγχος αερισμού καμπίνας ύπνου και επανέλεγχος παλμικής οξυμετρίας σε ηρεμία.</p>
        </div>
        """), unsafe_allow_html=True)

    if hrv < 25 or siga < 80 or glucose > 120:
        bio_alerts_triggered = True
        st.markdown(T(f"""
        <div class="alert-tier2">
            <h4> [TIER 2 NEUROENDOCRINE / IMMUNE ALERT] SYMPATHETIC HYPERACTIVATION & IMMUNE SUPPRESSION</h4>
            <p><b>Indicators:</b> HRV={hrv} ms (low), sIgA={siga} μg/mL, Glucose={glucose} mg/dL (high cortisol / risk of EBV/CMV reactivation).</p>
            <p><b>Immediate Solutions ({phase_name}):</b> {', '.join(phase_solutions)} Apply intensive aerobic exercise/ARED and relaxation techniques.</p>
        </div>
        """, f"""
        <div class="alert-tier2">
            <h4> [TIER 2 NEUROENDOCRINE / IMMUNE ALERT] ΣΥΜΠΑΘΗΤΙΚΗ ΥΠΕΡΔΙΕΓΕΡΣΗ & ΚΑΤΑΣΤΟΛΗ ΑΝΟΣΙΑΣ</h4>
            <p><b>Ενδείξεις:</b> HRV={hrv} ms (χαμηλό), sIgA={siga} μg/mL, Γλυκόζη={glucose} mg/dL (υψηλή κορτιζόλη / κίνδυνος επανενεργοποίησης EBV/CMV).</p>
            <p><b>Άμεσες Λύσεις ({phase_name}):</b> {', '.join(phase_solutions)} Εφαρμογή εντατικής αεροβικής άσκησης/ARED και τεχνικών χαλάρωσης.</p>
        </div>
        """), unsafe_allow_html=True)

    if not bio_alerts_triggered:
        st.markdown(T("""
        <div class="alert-nominal">
            <h4> [BIOMETRICS NOMINAL] PHYSIOLOGICAL & IMMUNOLOGICAL INDICATORS WITHIN LIMITS</h4>
            <p>HRV, SpO₂, glucose and secretory IgA indicate a balanced autonomic nervous and immune system.</p>
        </div>
        """, """
        <div class="alert-nominal">
            <h4>[BIOMETRICS NOMINAL] ΦΥΣΙΟΛΟΓΙΚΟΙ & ΑΝΟΣΟΛΟΓΙΚΟΙ ΔΕΙΚΤΕΣ ΕΝΤΟΣ ΟΡΙΩΝ</h4>
            <p>HRV, SpO₂, γλυκόζη και εκκριτική IgA υποδεικνύουν ισορροπημένο αυτόνομο νευρικό και ανοσοποιητικό σύστημα.</p>
        </div>
        """), unsafe_allow_html=True)

# ==============================================================================
# TAB 2: NEUROCOGNITION, SLEEP & COGNITIVE READINESS ALERTS (APP 2)
# ==============================================================================
with tabs[1]:
    col_n1, col_n2 = st.columns(2)

    with col_n1:
        st.subheader("NASA Psychomotor Vigilance Task (PVT-Brief)")
        st.caption(T("Objective measurement of neurocognitive readiness. Lapses > 500 ms.",
                     "Αντικειμενική μέτρηση νευρογνωστικής ετοιμότητας. Lapses > 500 ms."))

        if st.session_state.pvt_state == "IDLE":
            if st.button(T("🏁Start PVT Test", "🏁 Έναρξη Δοκιμής PVT"), type="primary"):
                with st.spinner(T("Waiting for random stimulus (2-4s)...", "Αναμονή τυχαίου ερεθίσματος (2-4s)...")):
                    time.sleep(random.uniform(1.5, 3.0))
                st.session_state.pvt_state = "STIMULUS"
                st.session_state.pvt_start_time = time.perf_counter()
                st.rerun()
        elif st.session_state.pvt_state == "STIMULUS":
            st.error(T(" VISUAL STIMULUS ACTIVE! PRESS NOW!", " ΟΠΤΙΚΟ ΕΡΕΘΙΣΜΑ ΕΝΕΡΓΟ! ΠΑΤΗΣΤΕ ΤΩΡΑ!"))
            if st.button(T(" RECORD RESPONSE (SPACE)", " ΚΑΤΑΓΡΑΦΗ ΑΝΤΙΔΡΑΣΗΣ (SPACE)"), type="primary"):
                rt_ms = int((time.perf_counter() - st.session_state.pvt_start_time) * 1000)
                st.session_state.pvt_results.append(rt_ms)
                st.session_state.pvt_state = "IDLE"
                st.session_state.xp += 15
                st.rerun()

        pvt_mean = int(sum(st.session_state.pvt_results) / len(st.session_state.pvt_results))
        pvt_lapses = sum(1 for x in st.session_state.pvt_results if x > 500)

        m1, m2 = st.columns(2)
        m1.metric(T("Mean Reaction Time", "Μέσος Χρόνος Αντίδρασης"), f"{pvt_mean} ms",
                  delta=f"{pvt_mean - 220} ms vs Baseline", delta_color="inverse")
        m2.metric(T("Lapses (> 500ms)", "Ολισθήματα (Lapses > 500ms)"), f"{pvt_lapses}")
        st.caption(T(f"Recent measurements (ms): {st.session_state.pvt_results[-5:]}",
                     f"Πρόσφατες μετρήσεις (ms): {st.session_state.pvt_results[-5:]}"))

        # --- PVT-BRIEF CLASSIFICATION (from group1.docx) ---
        # Group 1: mean RT 180–250 ms AND 0 lapses  -> Biological Homeostasis (Flight Ready)
        # Group 2: mean RT > 250 ms OR >= 1 lapse (> 500 ms) -> Biological Strain (Tier 1–3 Intervention)
        st.markdown(T("**PVT-Brief Assessment Group:**", "**Ομάδα Αξιολόγησης PVT-Brief:**"))

        if pvt_mean > 250 or pvt_lapses >= 1:
            st.markdown(T(f"""
                    <div class="alert-tier2">
                        <h4> GROUP 2: BIOLOGICAL STRAIN <i>(Cognitive &amp; Metabolic Strain)</i></h4>
                        <p><b>PVT-Brief limits:</b> &gt; 250 ms or ≥ 1 Lapse (&gt; 500 ms) — current: {pvt_mean} ms, {pvt_lapses} lapse(s).</p>
                        <p><b>Dominant biological impact:</b> Adenosine accumulation, possible hypoxia (cabin CO₂), stress axis (HPA) hyperactivation, drop in HRV/sIgA.</p>
                        <p><b>System decision:</b> Countermeasures / Grounding <i>(Tier 1–3 Intervention)</i></p>
                    </div>
                    """, f"""
                    <div class="alert-tier2">
                        <h4> ΟΜΑΔΑ 2: ΒΙΟΛΟΓΙΚΗ ΕΠΙΒΑΡΥΝΣΗ <i>(Cognitive &amp; Metabolic Strain)</i></h4>
                        <p><b>Όρια PVT-Brief:</b> &gt; 250 ms ή ≥ 1 Lapse (&gt; 500 ms) — τρέχον: {pvt_mean} ms, {pvt_lapses} lapse(s).</p>
                        <p><b>Κυρίαρχος βιολογικός αντίκτυπος:</b> Συσσώρευση αδενοσίνης, πιθανή υποξία (CO₂ καμπίνας), υπερδιέγερση άξονα στρες (HPA), πτώση HRV/sIgA.</p>
                        <p><b>Απόφαση συστήματος:</b> Αντίμετρα / Grounding <i>(Tier 1–3 Intervention)</i></p>
                    </div>
                    """), unsafe_allow_html=True)
        else:
            st.markdown(T(f"""
                    <div class="alert-nominal">
                        <h4> GROUP 1: BIOLOGICAL HOMEOSTASIS <i>(Optimal Readiness)</i></h4>
                        <p><b>PVT-Brief limits:</b> 180–250 ms &amp; 0 Lapses — current: {pvt_mean} ms, {pvt_lapses} lapses.</p>
                        <p><b>Dominant biological impact:</b> Optimal prefrontal cortex (DLPFC) function, cortisol/melatonin balance, normal HRV &amp; immune tone.</p>
                        <p><b>System decision:</b> Shift Approved <i>(Flight Ready)</i></p>
                    </div>
                    """, f"""
                    <div class="alert-nominal">
                        <h4> ΟΜΑΔΑ 1: ΒΙΟΛΟΓΙΚΗ ΟΜΟΙΟΣΤΑΣΗ <i>(Optimal Readiness)</i></h4>
                        <p><b>Όρια PVT-Brief:</b> 180–250 ms &amp; 0 Lapses — τρέχον: {pvt_mean} ms, {pvt_lapses} lapses.</p>
                        <p><b>Κυρίαρχος βιολογικός αντίκτυπος:</b> Βέλτιστη λειτουργία προμετωπιαίου φλοιού (DLPFC), ισορροπία κορτιζόλης/μελατονίνης, φυσιολογικός τόνος HRV &amp; ανοσίας.</p>
                        <p><b>Απόφαση συστήματος:</b> Έγκριση Βάρδιας <i>(Flight Ready)</i></p>
                    </div>
                    """), unsafe_allow_html=True)
            if pvt_mean < 180:
                st.caption(
                    T("Mean RT below 180 ms: possible anticipatory responses (pressing before the stimulus). Consider repeating the test.",
                      "Μέσος χρόνος κάτω από 180 ms: πιθανές πρόωρες αντιδράσεις (πάτημα πριν το ερέθισμα). Προτείνεται επανάληψη της δοκιμής."))
        if st.button(T("🔄 Restart PVT", "🔄 Επανεκκίνηση PVT")):
            defaults = {"Nominal": [0, 0, 0],
                        "Cumulative Isolation Stress": [305, 318, 307],
                        "Acute Deprivation / CO2 Pocket": [410, 525, 540]}
            st.session_state.pvt_results = defaults[st.session_state.preset].copy()
            st.session_state.pvt_state = "IDLE"
            st.rerun()
        st.divider()
        st.subheader(T("🗣 Passive Acoustic Biomarkers (Audio Log)", "🎙️ Παθητικοί Ακουστικοί Βιοδείκτες (Audio Log)"))
        st.write(T(f"**Fundamental Frequency (F0 Pitch):** `{p['voice_f0']}`",
                   f"**Θεμελιώδης Συχνότητα (F0 Pitch):** `{p['voice_f0']}`"))
        st.write(T(f"**Speech Pause Ratio:** `{p['voice_pause']}%` (Risk threshold: >25%)",
                   f"**Λόγος Παύσεων Ομιλίας (Pause Ratio):** `{p['voice_pause']}%` (Όριο κινδύνου: >25%)"))

    with col_n2:
        st.subheader(T(" Sleep Architecture & 30-Second VAS", " Αρχιτεκτονική Ύπνου & 30-Second VAS"))
        sleep_h = st.slider(T("Total Sleep Time - TST (hours)", "Συνολική Διάρκεια Ύπνου - TST (ώρες)"),
                            2.0, 10.0, float(p["sleep_h"]), 0.1)
        sleep_lat = st.slider(T("Sleep Onset Latency (minutes)", "Καθυστέρηση Επέλευσης Ύπνου (λεπτά)"),
                              0, 90, int(p["sleep_lat"]))

        st.markdown("**30-Second Visual Analog Scale (VAS 0–100):**")
        vas_energy = st.slider(T("Energy / Alertness", "Ενέργεια / Εγρήγορση"), 0, 100, p["vas_energy"])
        vas_mood = st.slider(T("Emotional Mood (Valence)", "Συναισθηματική Διάθεση (Valence)"), 0, 100, p["vas_mood"])
        vas_stress = st.slider(T("Stress Level", "Επίπεδο Στρες"), 0, 100, p["vas_stress"])
        vas_social = st.slider(T("Social Connectedness", "Κοινωνική Σύνδεση"), 0, 100, p["vas_social"])

        swi = round((vas_energy + vas_mood + (100 - vas_stress) + vas_social) / 4, 1)
        st.metric("Subjective Well-being Index (SWI)", f"{swi} / 100")

    # --- INTEGRATED CRS CALCULATION & NEUROCOGNITIVE ALERTS IN TAB 2 ---
    st.divider()
    st.subheader(T(" Cognitive Readiness Score (CRS) & Immediate Solutions",
                   " Δείκτης Νευρογνωστικής Ετοιμότητας (CRS) & Άμεσες Λύσεις"))

    pvt_score = max(0, min(100, 100 - max(0, (pvt_mean - 220) // 10) * 3 - (pvt_lapses * 15)))
    sleep_score = 100 if sleep_h >= 7.5 else (75 if sleep_h >= 6.0 else 30)

    if sex == "Male":
        crs = round(0.45 * pvt_score + 0.35 * sleep_score + 0.20 * swi, 1)
        sex_note = T("Male Profile weight adjustment (45% PVT / 35% Sleep / 20% Self-Report) due to a tendency toward under-reporting.",
                     "Προσαρμογή βαρών Male Profile (45% PVT / 35% Sleep / 20% Self-Report) λόγω τάσης υποκαταγραφής (under-reporting).")
    else:
        crs = round(0.35 * pvt_score + 0.35 * sleep_score + 0.30 * swi, 1)
        sex_note = T("Female Profile weight adjustment (35% PVT / 35% Sleep / 30% Self-Report) with increased sensitivity to Sleep Latency.",
                     "Προσαρμογή βαρών Female Profile (35% PVT / 35% Sleep / 30% Self-Report) με αυξημένη ευαισθησία στο Sleep Latency.")

    c_res1, c_res2, c_res3, c_res4 = st.columns(4)
    c_res1.metric("Cognitive Readiness (CRS)", f"{crs} / 100")
    c_res2.metric("PVT Objective Score", f"{pvt_score} / 100")
    c_res3.metric("Sleep Architecture Score", f"{sleep_score} / 100")
    c_res4.metric("Subjective Well-being (SWI)", f"{swi} / 100")
    st.caption(f"ℹ️ {sex_note}")

    if crs < 50 or pvt_lapses >= 3:
        st.markdown(T(f"""
        <div class="alert-tier3">
            <h4> [TIER 3 CRITICAL] ACUTE COGNITIVE EXHAUSTION / CREW DISQUALIFICATION</h4>
            <p><b>Safety Interlock (Grounding Protocol):</b> Immediate prohibition from operating the robotic arm (Canadarm), docking procedures and EVA. Mandatory adherence to safety checklists.</p>
            <p><b>Immediate Solutions ({phase_name}):</b> Mandatory 8-hour recovery sleep, strict adherence to the sleep schedule and communication with ground psychologists / family.</p>
        </div>
        """, f"""
        <div class="alert-tier3">
            <h4> [TIER 3 CRITICAL] ACUTE COGNITIVE EXHAUSTION / CREW DISQUALIFICATION</h4>
            <p><b>Δικλίδα Ασφαλείας (Grounding Protocol):</b> Άμεση απαγόρευση χειρισμού ρομποτικού βραχίονα (Canadarm), διαδικασιών πρόσδεσης (docking) και EVA. Υποχρεωτική τήρηση λιστών ελέγχου (checklists) ασφαλείας.</p>
            <p><b>Άμεσες Λύσεις ({phase_name}):</b> Υποχρεωτικός ύπνος ανάκαμψης 8 ωρών, αυστηρή τήρηση προγράμματος ύπνου και επικοινωνία με ψυχολόγους εδάφους / οικογένεια.</p>
        </div>
        """), unsafe_allow_html=True)
    elif crs < 70 or vas_stress > 75:
        st.markdown(T(f"""
        <div class="alert-tier2">
            <h4> [TIER 2 CAUTION] ELEVATED COGNITIVE WORKLOAD & SENSORY UNDERSTIMULATION</h4>
            <p><b>Immediate Solutions ({phase_name}):</b> Rotation of roles and duties to prevent boredom, dynamic LED lighting adjustment on the station, Earth observation from the Cupola and a 20' Power Nap.</p>
        </div>
        """, f"""
        <div class="alert-tier2">
            <h4> [TIER 2 CAUTION] ELEVATED COGNITIVE WORKLOAD & SENSORY UNDERSTIMULATION</h4>
            <p><b>Άμεσες Λύσεις ({phase_name}):</b> Εναλλαγή ρόλων και καθηκόντων για αποφυγή πλήξης, ρύθμιση δυναμικού φωτισμού LED στο σταθμό, παρατήρηση της Γης από τον θόλο (Cupola) και 20' Power Nap.</p>
        </div>
        """), unsafe_allow_html=True)
    elif sleep_h < 6.0:
        st.markdown(T("""
        <div class="alert-tier1">
            <h4> [TIER 1 ADVISORY] SLEEP DEBT & CIRCADIAN MISALIGNMENT</h4>
            <p><b>Immediate Solution:</b> Dynamic LED lighting adjustment (460–480 nm blue light in the morning) and strict adherence to the sleep and break schedule.</p>
        </div>
        """, """
        <div class="alert-tier1">
            <h4> [TIER 1 ADVISORY] SLEEP DEBT & CIRCADIAN MISALIGNMENT</h4>
            <p><b>Άμεση Λύση:</b> Ρύθμιση δυναμικού φωτισμού LED (μπλε φως 460–480 nm το πρωί) και αυστηρή τήρηση προγράμματος ύπνου και διαλείμματος.</p>
        </div>
        """), unsafe_allow_html=True)
    else:
        st.markdown(T("""
        <div class="alert-nominal">
            <h4> [NOMINAL STATUS] FLIGHT READY — OPTIMAL NEUROCOGNITIVE READINESS</h4>
            <p>Cognitive vigilance and sleep architecture are at optimal levels.</p>
        </div>
        """, """
        <div class="alert-nominal">
            <h4> [NOMINAL STATUS] FLIGHT READY — OPTIMAL NEUROCOGNITIVE READINESS</h4>
            <p>Η γνωστική επαγρύπνηση και η αρχιτεκτονική ύπνου βρίσκονται σε βέλτιστα επίπεδα.</p>
        </div>
        """), unsafe_allow_html=True)

# ==============================================================================
# TAB 3: STRAIN QUESTIONNAIRE (Q1-Q15), ALLOSTATIC LOAD & JSON EXPORT
# ==============================================================================
with tabs[2]:
    st.subheader(T(" Biological & Psychosocial Strain Assessment (Q1–Q15)",
                   " Αξιολόγηση Βιολογικής & Ψυχοκοινωνικής Επιβάρυνσης (Ε1–Ε15)"))
    st.caption(T("Conversion of responses into a Strain Index (0 = None, 100 = Maximum) with a Temporal Persistence Multiplier.",
                 "Μετατροπή απαντήσεων σε Δείκτη Επιβάρυνσης (0 = Καμία, 100 = Μέγιστη) με Πολλαπλασιαστή Χρονικής Επιμονής."))

    duration_days = st.slider(T("Duration of elevated score (Days - Persistence Multiplier):",
                                "Διάρκεια παραμονής υψηλού σκορ (Ημέρες - Πολλαπλασιαστής Επιμονής):"),
                              1, 14, p["duration_days"])

    nominal = st.session_state.preset == "Nominal"

    col_q1, col_q2 = st.columns(2)
    with col_q1:
        st.markdown(T("**1. Neuroendocrine Axis (Q7, Q8, Q3)**", "**1. Νευροενδοκρινικός Άξονας (Ε7, Ε8, Ε3)**"))
        e3 = st.slider(T("[Q3] Difficulty falling asleep (1=Immediately, 10=Awake for hours)",
                         "[Ε3] Δυσκολία αποκοίμησης (1=Αμέσως, 10=Ώρες ξύπνιος)"), 1, 10, 3 if nominal else 8)
        e7 = st.slider(T("[Q7] Inner anxiety (1=Relaxed, 10=Unbearable anxiety)",
                         "[Ε7] Εσωτερικό άγχος (1=Χαλάρωση, 10=Αφόρητο άγχος)"), 1, 10, 2 if nominal else 8)
        e8 = st.slider(T("[Q8] Sense of control over schedule (1=None, 10=Complete)",
                         "[Ε8] Αίσθηση ελέγχου προγράμματος (1=Καθόλου, 10=Πλήρης)"), 1, 10, 9 if nominal else 4)

        st.markdown(T("**2. Immune & Inflammatory Profile (Q1, Q12, Q13, Q15)**",
                      "**2. Ανοσολογικό & Φλεγμονώδες Προφίλ (Ε1, Ε12, Ε13, Ε15)**"))
        e12 = st.slider(T("[Q12] Crew cooperation climate (1=Tension, 10=Harmony)",
                          "[Ε12] Κλίμα συνεργασίας πληρώματος (1=Ένταση, 10=Αρμονία)"), 1, 10, 9 if nominal else 4)
        e13 = st.slider(T("[Q13] Emotional isolation (1=None, 10=Absolute)",
                          "[Ε13] Συναισθηματική απομόνωση (1=Καθόλου, 10=Απόλυτη)"), 1, 10, 2 if nominal else 8)
        e15 = st.slider(T("[Q15] Stomach discomfort / Gut axis (1=None, 10=Severe)",
                          "[Ε15] Στομαχικές ενοχλήσεις / Άξονας εντέρου (1=Καμία, 10=Σοβαρή)"), 1, 10, 1 if nominal else 6)

    with col_q2:
        st.markdown(T("**3. CNS & Neurotransmitters (Q2, Q4, Q5, Q10, Q11)**",
                      "**3. ΚΝΣ & Νευροδιαβιβαστές (Ε2, Ε4, Ε5, Ε10, Ε11)**"))
        e2 = st.slider(T("[Q2] Refreshed after sleep (1=Exhausted, 10=Fully)",
                         "[Ε2] Αναζωογόνηση μετά τον ύπνο (1=Εξαντλημένος, 10=Πλήρως)"), 1, 10, 8 if nominal else 3)
        e4 = st.slider(T("[Q4] General mood (1=Depressed, 10=Very positive)",
                         "[Ε4] Γενική διάθεση (1=Καταθλιπτική, 10=Πολύ θετική)"), 1, 10, 9 if nominal else 4)
        e5 = st.slider(T("[Q5] Interest & meaning in duties (1=None, 10=Intense)",
                         "[Ε5] Ενδιαφέρον & νόημα καθηκόντων (1=Καθόλου, 10=Έντονο)"), 1, 10, 9 if nominal else 4)
        e10 = st.slider(T("[Q10] Physical energy / Adenosine (1=Lethargy, 10=Maximum)",
                          "[Ε10] Φυσική ενέργεια / Αδενοσίνη (1=Λήθαργος, 10=Μέγιστη)"), 1, 10, 8 if nominal else 3)
        e11 = st.slider(T("[Q11] Concentration / DLPFC (1=Foggy, 10=Clear)",
                          "[Ε11] Συγκέντρωση / DLPFC (1=Θολούρα, 10=Διαύγεια)"), 1, 10, 9 if nominal else 4)

        st.markdown(T("**4. Autonomic & Musculoskeletal (Q6, Q9, Q14)**",
                      "**4. Αυτόνομο & Μυοσκελετικό (Ε6, Ε9, Ε14)**"))
        e6 = st.slider(T("[Q6] Irritability (1=Calm, 10=Extremely irritable)",
                         "[Ε6] Ευερεθιστότητα (1=Ηρεμία, 10=Εξαιρετικά ευερέθιστος)"), 1, 10, 2 if nominal else 7)
        e9 = st.slider(T("[Q9] Workload demand (1=Minimal, 10=Excessive)",
                         "[Ε9] Απαιτητικότητα όγκου εργασίας (1=Ελάχιστος, 10=Υπερβολικός)"), 1, 10, 4 if nominal else 8)
        e14 = st.checkbox(T("[Q14] Neck muscle stiffness / headache?",
                            "[Ε14] Μυϊκή δυσκαμψία στον αυχένα / πονοκέφαλος;"), value=not nominal)

    pos_strain = lambda x: (10 - x) * 11.1
    neg_strain = lambda x: (x - 1) * 11.1
    sleep_strain = 0 if sleep_h >= 7.5 else max(0, (7.0 - sleep_h) * 25)

    hpa_strain = round((neg_strain(e3) + neg_strain(e7) + pos_strain(e8)) / 3, 1)
    imm_strain = round((sleep_strain + pos_strain(e12) + neg_strain(e13) + neg_strain(e15)) / 4, 1)
    cns_strain = round((pos_strain(e2) + pos_strain(e4) + pos_strain(e5) + pos_strain(e10) + pos_strain(e11)) / 5, 1)
    ans_strain = round((neg_strain(e6) + neg_strain(e9) + (100 if e14 else 0)) / 3, 1)

    st.divider()
    s1, s2, s3, s4 = st.columns(4)
    s1.metric(T("Neuroendocrine (HPA)", "Νευροενδοκρινικός (HPA)"), f"{hpa_strain}/100")
    s2.metric(T("Immune Profile", "Ανοσολογικό Προφίλ"), f"{imm_strain}/100")
    s3.metric(T("CNS & Neurotransmitters", "ΚΝΣ & Νευροδιαβιβαστές"), f"{cns_strain}/100")
    s4.metric(T("Autonomic & Musculoskeletal", "Αυτόνομο & Μυοσκελετικό"), f"{ans_strain}/100")

    # --- INTEGRATED ALLOSTATIC LOAD ALERTS & SOLUTIONS ---
    st.subheader(T(" Allostatic Load Assessment & Immediate Countermeasures",
                   " Αξιολόγηση Αλλοστατικού Φορτίου & Άμεσα Αντίμετρα"))

    if duration_days >= 7 or max(hpa_strain, imm_strain, cns_strain, ans_strain) > 65:
        st.markdown(T(f"""
        <div class="alert-tier3">
            <h4> [TIER 3 ALLOSTATIC LOAD ALERT] CHRONIC STRAIN ({duration_days} DAYS) — RISK OF BURNOUT & IMMUNOSUPPRESSION</h4>
            <p><b>Biological Interpretation:</b> Prolonged hypercortisolemia, dopamine/serotonin decline, immunosuppression and high risk of human error.</p>
            <p><b>Recommended Immediate Solutions ({phase_name}):</b></p>
            <ul>
                <li><b>Social Cohesion & Decompression:</b> Mandatory technology-free crew meals & continuous communication with family / ground psychologists.</li>
                <li><b>Psychobiological Uplift:</b> Earth observation from the Cupola & exposure to novel stimuli (surprise items in supplies, games).</li>
                <li><b>Physical & Circadian Regulation:</b> Intensive aerobic exercise and strength training (ARED), dynamic LED lighting adjustment & a mandatory rest day.</li>
            </ul>
        </div>
        """, f"""
        <div class="alert-tier3">
            <h4> [TIER 3 ALLOSTATIC LOAD ALERT] ΧΡΟΝΙΑ ΕΠΙΒΑΡΥΝΣΗ ({duration_days} ΗΜΕΡΕΣ) — ΚΙΝΔΥΝΟΣ BURNOUT & ΑΝΟΣΟΚΑΤΑΣΤΟΛΗΣ</h4>
            <p><b>Βιολογική Ερμηνεία:</b> Παρατεταμένη υπερκορτιζολαιμία, πτώση ντοπαμίνης/σεροτονίνης, ανοσοκαταστολή και υψηλό ρίσκο ανθρώπινου λάθους.</p>
            <p><b>Προτεινόμενες Άμεσες Λύσεις ({phase_name}):</b></p>
            <ul>
                <li><b>Κοινωνική Συνοχή & Αποφόρτιση:</b> Υποχρεωτικά ομαδικά γεύματα χωρίς τεχνολογία & συνεχής επικοινωνία με την οικογένεια / ψυχολόγους εδάφους.</li>
                <li><b>Ψυχοβιολογική Ανάταση:</b> Παρατήρηση της Γης από τον θόλο (Cupola) & έκθεση σε νέα ερεθίσματα (έκπληξη σε προμήθειες, παιχνίδια).</li>
                <li><b>Σωματική & Κιρκάδια Ρύθμιση:</b> Εντατική αεροβική άσκηση και ενδυνάμωση (ARED), ρύθμιση δυναμικού φωτισμού LED & υποχρεωτική ημέρα ανάπαυσης.</li>
            </ul>
        </div>
        """), unsafe_allow_html=True)
    elif duration_days >= 3 or max(hpa_strain, imm_strain, cns_strain, ans_strain) > 45:
        st.markdown(T(f"""
        <div class="alert-tier2">
            <h4> [TIER 2 ALLOSTATIC STRAIN] MODERATE STRAIN ({duration_days} DAYS)</h4>
            <p><b>Biological Interpretation:</b> The body struggles to return to a resting state (onset of sleep and digestive disturbances).</p>
            <p><b>Immediate Solutions:</b> Rotation of roles and duties to prevent boredom, use of music and relaxation techniques, and strict adherence to breaks.</p>
        </div>
        """, f"""
        <div class="alert-tier2">
            <h4> [TIER 2 ALLOSTATIC STRAIN] ΜΕΤΡΙΑ ΕΠΙΒΑΡΥΝΣΗ ({duration_days} ΗΜΕΡΕΣ)</h4>
            <p><b>Βιολογική Ερμηνεία:</b> Το σώμα δυσκολεύεται να επιστρέψει σε ηρεμία (αρχή διαταραχών ύπνου και πέψης).</p>
            <p><b>Άμεσες Λύσεις:</b> Εναλλαγή ρόλων και καθηκόντων για αποφυγή πλήξης, χρήση μουσικής και τεχνικών χαλάρωσης, και αυστηρή τήρηση διαλειμμάτων.</p>
        </div>
        """), unsafe_allow_html=True)
    else:
        st.markdown(T("""
        <div class="alert-nominal">
            <h4> [TIER 1 / NOMINAL] NORMAL ADAPTATION (1–2 DAYS)</h4>
            <p>The body is maintaining homeostasis. Continue regular exercise (ARED), dynamic LED lighting and crew meals.</p>
        </div>
        """, """
        <div class="alert-nominal">
            <h4> [TIER 1 / NOMINAL] ΦΥΣΙΟΛΟΓΙΚΗ ΠΡΟΣΑΡΜΟΓΗ (1–2 ΗΜΕΡΕΣ)</h4>
            <p>Ο οργανισμός διατηρεί την ομοιόσταση. Συνεχίστε την τακτική άσκηση (ARED), τον δυναμικό φωτισμό LED και τα ομαδικά γεύματα πληρώματος.</p>
        </div>
        """), unsafe_allow_html=True)
