from signal_scout.classifiers import brief_summary_from

def test_brief_summary_length():
    title = "City launches healthy food pricing pilot"
    summary = "The council will pilot discounts of 20% on healthy foods for 12 weeks in the UK starting this month."
    s = brief_summary_from(title, summary)
    assert len(s.split()) <= 28

def test_brief_summary_contains_action_number():
    title = "New UPF label study"
    summary = "Randomized trial with 1,200 participants finds 15% drop in UPF purchases."
    s = brief_summary_from(title, summary)
    text = s.lower()
    assert "trial" in text or "randomized" in text
    assert "15%" in text or "1,200" in text
