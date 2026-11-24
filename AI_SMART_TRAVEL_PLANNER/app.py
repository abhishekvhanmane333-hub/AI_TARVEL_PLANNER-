import os
import io
import html
import requests
import pandas as pd
import pydeck as pdk
import streamlit as st

from dotenv import load_dotenv
from groq import Groq
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

# =====================================================
# CONFIGURATION
# =====================================================

load_dotenv()

st.set_page_config(
    page_title="AI Smart Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

HEADERS = {
    "User-Agent": "AISmartTravelPlanner/1.0"
}


# =====================================================
# UI STYLING
# =====================================================

st.markdown("""
<style>
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background-color: #F1F5FB !important;
}

.stApp p,
.stApp label,
.stApp li {
    color: #172B4D !important;
}

.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4 {
    color: #102A43 !important;
    -webkit-text-fill-color: #102A43 !important;
    font-weight: 750 !important;
}

[data-testid="stSidebar"],
[data-testid="stSidebar"] > div {
    background-color: #DFE9F5 !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #172B4D !important;
    -webkit-text-fill-color: #172B4D !important;
}

.stTextInput label,
.stNumberInput label,
.stDateInput label,
.stSelectbox label,
.stTextArea label {
    color: #172B4D !important;
    font-weight: 700 !important;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea {
    background-color: #FFFFFF !important;
    color: #172B4D !important;
    -webkit-text-fill-color: #172B4D !important;
    border: 2px solid #7D96B2 !important;
    border-radius: 8px !important;
}

[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border: 2px solid #7D96B2 !important;
}

[data-testid="stSelectbox"] [data-baseweb="select"] *,
[data-testid="stSelectbox"] input {
    color: #172B4D !important;
    -webkit-text-fill-color: #172B4D !important;
    opacity: 1 !important;
}

[data-testid="stSelectbox"] svg,
[data-testid="stDateInput"] svg {
    color: #172B4D !important;
    fill: #172B4D !important;
}

[data-testid="stNumberInput"] button {
    background-color: #DCE8F6 !important;
    color: #102A43 !important;
}

.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] button {
    background-color: #1769D2 !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border: 1px solid #1255AE !important;
    border-radius: 9px !important;
    min-height: 44px !important;
    font-weight: 750 !important;
}

.stButton > button *,
.stDownloadButton > button *,
[data-testid="stFormSubmitButton"] button * {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.hero-banner {
    background: linear-gradient(120deg, #10264F, #1769D2) !important;
    padding: 30px !important;
    border-radius: 18px !important;
    margin-bottom: 22px !important;
}

.hero-banner h1,
.hero-banner p {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.hero-banner h1 {
    font-size: 36px !important;
    font-weight: 800 !important;
}

.hero-banner p {
    font-size: 17px !important;
    line-height: 1.6 !important;
}

.info-box {
    background-color: #DCECFB !important;
    border-left: 5px solid #1769D2 !important;
    padding: 18px !important;
    border-radius: 10px !important;
}

.info-box p,
.info-box strong {
    color: #17365D !important;
}

.result-card {
    background-color: #FFFFFF !important;
    border: 1px solid #C7D6E7 !important;
    border-radius: 12px !important;
    padding: 18px !important;
    margin-bottom: 14px !important;
}

.result-card h3,
.result-card p {
    color: #172B4D !important;
}

[data-testid="stMetric"] {
    background-color: #FFFFFF !important;
    border: 1px solid #C7D6E7 !important;
    border-radius: 12px !important;
    padding: 16px !important;
}

[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] *,
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {
    color: #172B4D !important;
    -webkit-text-fill-color: #172B4D !important;
}

.app-footer {
    border-top: 1px solid #C7D6E7;
    margin-top: 40px;
    padding-top: 18px;
    color: #334E68 !important;
    font-size: 13px;
    line-height: 1.8;
}

.app-footer p {
    color: #334E68 !important;
}

@media (max-width: 768px) {
    .hero-banner h1 {
        font-size: 27px !important;
    }
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# GEOCODING
# =====================================================

def get_coordinates(place):
    """Find a location using OpenStreetMap."""

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": place,
                "format": "json",
                "limit": 1
            },
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()
        results = response.json()

        if not results:
            return None

        return {
            "name": place,
            "latitude": float(results[0]["lat"]),
            "longitude": float(results[0]["lon"]),
            "display_name": results[0]["display_name"]
        }

    except (requests.RequestException, ValueError, KeyError):
        return None


# =====================================================
# ROAD ROUTE BETWEEN TWO LOCATIONS
# =====================================================

def get_leg_route(start_point, end_point):
    """Return road route geometry and distance for one journey leg."""

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{start_point['longitude']},{start_point['latitude']};"
        f"{end_point['longitude']},{end_point['latitude']}"
    )

    try:
        response = requests.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson"
            },
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            return None

        route = data["routes"][0]

        return {
            "distance_km": route["distance"] / 1000,
            "duration_hours": route["duration"] / 3600,
            "coordinates": route["geometry"]["coordinates"]
        }

    except (requests.RequestException, ValueError, KeyError):
        return None


# =====================================================
# MULTI-CITY ROUTE
# =====================================================

def get_multi_route(start, destinations):
    """
    Example:
    Solapur -> Pune -> Mumbai -> Nashik

    Calculates each road leg and combines its road geometry.
    """

    places = [start] + destinations
    points = []

    # Find coordinates for every location.
    for place in places:
        point = get_coordinates(place)

        if point is None:
            return {
                "error": f"Location not found: {place}"
            }

        points.append(point)

    total_distance = 0.0
    total_duration = 0.0
    all_paths = []
    legs = []

    # Calculate every individual road leg.
    for index in range(len(points) - 1):
        start_point = points[index]
        end_point = points[index + 1]

        leg = get_leg_route(start_point, end_point)

        if leg is None:
            return {
                "error": (
                    "Road route could not be calculated between "
                    f"{places[index]} and {places[index + 1]}."
                )
            }

        total_distance += leg["distance_km"]
        total_duration += leg["duration_hours"]

        all_paths.append(leg["coordinates"])

        legs.append({
            "from": places[index],
            "to": places[index + 1],
            "distance_km": round(leg["distance_km"], 2),
            "duration_hours": round(leg["duration_hours"], 2)
        })

    return {
        "places": places,
        "points": points,
        "legs": legs,
        "distance_km": round(total_distance, 2),
        "duration_hours": round(total_duration, 2),
        "paths": all_paths
    }


# =====================================================
# BUDGET CALCULATOR
# =====================================================

def calculate_budget(
    travel_mode,
    distance_km,
    travellers,
    duration_days,
    fuel_price,
    mileage,
    bus_fare,
    food_per_day,
    hotel_per_night,
    hotel_rooms,
    other_expenses
):
    if travel_mode == "Own Vehicle":
        transport = (
            (distance_km * 2 / mileage) * fuel_price
            if mileage > 0 else 0
        )
    else:
        transport = bus_fare * travellers

    food = food_per_day * travellers * duration_days

    # Assumes the trip starts on day one and ends after duration_days.
    hotel_nights = max(duration_days - 1, 0)
    hotel = hotel_per_night * hotel_rooms * hotel_nights

    total = transport + food + hotel + other_expenses

    return {
        "transport": round(transport, 2),
        "food": round(food, 2),
        "hotel": round(hotel, 2),
        "other": round(other_expenses, 2),
        "total": round(total, 2),
        "per_person": round(total / max(travellers, 1), 2)
    }


# =====================================================
# GROQ AI ITINERARY
# =====================================================

def generate_itinerary(
    start,
    destinations,
    travel_mode,
    travel_date,
    duration_days,
    travellers,
    budget,
    route
):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return (
            "AI itinerary is unavailable because GROQ_API_KEY "
            "was not found in the .env file. Your route and "
            "budget calculations can still work."
        )

    legs_text = "No road-route data available."

    if route and route.get("legs"):
        legs_text = "\n".join(
            f"{leg['from']} to {leg['to']}: "
            f"{leg['distance_km']} km"
            for leg in route["legs"]
        )

    prompt = f"""
You are a practical travel planning assistant.

Starting location: {start}
Destinations in order: {", ".join(destinations)}
Travel mode: {travel_mode}
Travel date: {travel_date}
Trip duration: {duration_days} days
Number of travellers: {travellers}
Estimated group budget: Rs. {budget:,.2f}

Road route estimates:
{legs_text}

Create a useful itinerary for the entire trip.

Requirements:
1. Follow the destination order provided.
2. Divide activities across the available days.
3. Include practical travel and rest suggestions.
4. Recommend sensible sightseeing and meal breaks.
5. Keep the budget in mind.
6. Do not claim live prices or hotel availability.
7. Do not invent exact ticket prices.
8. Advise the user to verify current prices and opening hours.
9. Use headings and bullet points.
"""

    try:
        client = Groq(api_key=api_key)

        for model in [
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b"
        ]:
            try:
                result = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an accurate travel planner. "
                                "Clearly label estimates and follow "
                                "the user's destination order."
                            )
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.5,
                    max_tokens=2000
                )

                return result.choices[0].message.content

            except Exception:
                continue

        return (
            "The Groq AI service is currently unavailable. "
            "Please check the API key, model availability and "
            "internet connection, then try again."
        )

    except Exception:
        return (
            "AI itinerary could not be generated. Please check "
            "your Groq API configuration."
        )


# =====================================================
# PDF REPORT
# =====================================================

def create_pdf(
    start,
    destinations,
    travel_mode,
    travel_date,
    duration_days,
    travellers,
    route,
    budget,
    itinerary
):
    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=38,
        leftMargin=38,
        topMargin=38,
        bottomMargin=38
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TravelTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#102A56"),
        alignment=TA_CENTER,
        fontSize=21,
        leading=27
    )

    heading_style = ParagraphStyle(
        "TravelHeading",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#1769D2"),
        fontSize=13,
        leading=18,
        spaceBefore=12,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        "TravelBody",
        parent=styles["BodyText"],
        textColor=colors.HexColor("#172B4D"),
        fontSize=9,
        leading=14,
        spaceAfter=6
    )

    story = [
        Paragraph("AI Smart Travel Planner", title_style),
        Spacer(1, 12),
        Paragraph("Trip Summary", heading_style)
    ]

    destination_text = " → ".join([start] + destinations)

    summary = [
        ["Route", destination_text],
        ["Travel Mode", travel_mode],
        ["Travel Date", str(travel_date)],
        ["Duration", f"{duration_days} days"],
        ["Travellers", str(travellers)]
    ]

    if route and route.get("distance_km") is not None:
        summary.append([
            "Total Road Distance",
            f"{route['distance_km']:,.2f} km"
        ])

    summary_table = Table(summary, colWidths=[140, 355])

    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#DCE8F6")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#172B4D")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C5D4E6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 7)
    ]))

    story.extend([
        summary_table,
        Spacer(1, 12),
        Paragraph("Route Details", heading_style)
    ])

    if route and route.get("legs"):
        for leg in route["legs"]:
            story.append(Paragraph(
                f"{html.escape(leg['from'])} to "
                f"{html.escape(leg['to'])}: "
                f"{leg['distance_km']:,.2f} km; "
                f"estimated driving time "
                f"{leg['duration_hours']:.1f} hours",
                body_style
            ))
    else:
        story.append(
            Paragraph("Route details unavailable.", body_style)
        )

    story.append(Paragraph("Estimated Budget", heading_style))

    budget_rows = [
        ["Expense", "Estimated Cost (Rs.)"],
        ["Transport", f"{budget['transport']:,.2f}"],
        ["Food", f"{budget['food']:,.2f}"],
        ["Hotel", f"{budget['hotel']:,.2f}"],
        ["Other Expenses", f"{budget['other']:,.2f}"],
        ["Total", f"{budget['total']:,.2f}"],
        ["Per Person", f"{budget['per_person']:,.2f}"]
    ]

    budget_table = Table(budget_rows, colWidths=[245, 250])

    budget_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1769D2")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#172B4D")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C5D4E6")),
        ("PADDING", (0, 0), (-1, -1), 7)
    ]))

    story.extend([
        budget_table,
        Spacer(1, 12),
        Paragraph("AI Travel Itinerary", heading_style)
    ])

    safe_itinerary = html.escape(itinerary).replace("\n", "<br/>")
    story.append(Paragraph(safe_itinerary, body_style))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Disclaimer: All route, cost and AI recommendations are estimates. "
        "Verify current transport fares, accommodation prices, opening "
        "hours and travel conditions before departure.",
        body_style
    ))

    document.build(story)
    buffer.seek(0)

    return buffer.getvalue()


# =====================================================
# HEADER
# =====================================================

st.markdown("""
<div class="hero-banner">
    <h1>✈️ AI Smart Travel Planner</h1>
    <p>
        Plan multi-city journeys, estimate travel expenses,
        explore connected road routes and generate an AI itinerary.
    </p>
</div>
""", unsafe_allow_html=True)


# =====================================================
# SIDEBAR INPUT FORM
# =====================================================

st.sidebar.title("Trip Details")
st.sidebar.write("Enter your journey information below.")

with st.sidebar.form("travel_form"):

    starting_location = st.text_input(
        "Starting Location",
        placeholder="e.g. Solapur"
    )

    destinations_input = st.text_input(
        "Destinations",
        placeholder="Pune, Mumbai, Nashik",
        help=(
            "Enter multiple destinations separated by commas. "
            "The route will follow the order you enter."
        )
    )

    
    travel_mode = st.selectbox(
        "Travel Mode",
        ["Own Vehicle", "Bus", "Other Public Transport"]
    )

    travel_date = st.date_input("Travel Date")

    duration_days = st.number_input(
        "Trip Duration (Days)",
        min_value=1,
        max_value=60,
        value=3
    )

    travellers = st.number_input(
        "Number of Travellers",
        min_value=1,
        max_value=100,
        value=2
    )

    st.markdown("---")
    st.subheader("Transport Expenses")

    fuel_price = st.number_input(
        "Fuel Price per Litre (Rs.)",
        min_value=0.0,
        value=105.0,
        step=1.0
    )

    mileage = st.number_input(
        "Vehicle Mileage (km/litre)",
        min_value=1.0,
        value=40.0,
        step=1.0
    )

    bus_fare = st.number_input(
        "Bus Fare per Person (Rs.) - Entire Trip",
        min_value=0.0,
        value=500.0,
        step=50.0
    )

    st.markdown("---")
    st.subheader("Budget Settings")

    food_per_day = st.number_input(
        "Food per Person per Day (Rs.)",
        min_value=0.0,
        value=300.0,
        step=50.0
    )

    hotel_per_night = st.number_input(
        "Hotel per Room per Night (Rs.)",
        min_value=0.0,
        value=1500.0,
        step=100.0
    )

    hotel_rooms = st.number_input(
        "Number of Hotel Rooms",
        min_value=0,
        max_value=50,
        value=1
    )

    other_expenses = st.number_input(
        "Other Expenses for Entire Trip (Rs.)",
        min_value=0.0,
        value=500.0,
        step=100.0
    )

    submitted = st.form_submit_button(
        "Plan My Trip",
        use_container_width=True
    )


# =====================================================
# HOME SCREEN
# =====================================================

if not submitted:
    st.markdown("""
    <div class="info-box">
        <p>
        <strong>Ready for your next adventure?</strong><br>
        Enter your starting city and one or more destinations in the
        sidebar. Separate destinations with commas, in travel order.
        Then click Plan My Trip.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("What You Can Do")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("""
        <div class="result-card">
            <h3>🗺️ Multi-City Route</h3>
            <p>View a connected road route between multiple cities.</p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="result-card">
            <h3>💰 Budget Planner</h3>
            <p>Estimate transport, food, hotel and other expenses.</p>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <div class="result-card">
            <h3>🤖 AI Itinerary</h3>
            <p>Generate a day-by-day plan for your multi-city trip.</p>
        </div>
        """, unsafe_allow_html=True)


# =====================================================
# PROCESS SUBMITTED TRIP
# =====================================================

if submitted:

    destinations = [
        item.strip()
        for item in destinations_input.split(",")
        if item.strip()
    ]

    if not starting_location.strip():
        st.error("Please enter your Starting Location.")

    elif not destinations:
        st.error(
            "Please enter at least one destination, such as Pune."
        )

    else:
        all_places = [starting_location.strip()] + destinations

        # Detect repeated consecutive locations.
        if any(
            all_places[i].casefold() == all_places[i + 1].casefold()
            for i in range(len(all_places) - 1)
        ):
            st.error(
                "Two consecutive locations are the same. "
                "Please check your route."
            )

        else:
            with st.spinner(
                "Finding locations and connecting road routes..."
            ):
                route = get_multi_route(
                    starting_location.strip(),
                    destinations
                )

            st.subheader("🗺️ Your Multi-City Route")

            if route and route.get("error"):
                st.error(route["error"])
                st.info(
                    "Try using city names, for example "
                    "'Solapur' and 'Pune'."
                )

            else:
                st.markdown(
                    '<div class="info-box"><p><strong>Travel order</strong><br>'
                    + html.escape(" → ".join(route["places"]))
                    + '</p></div>',
                    unsafe_allow_html=True
                )

                # Total route metrics.
                c1, c2 = st.columns(2)

                c1.metric(
                    "Total Road Distance",
                    f"{route['distance_km']:,.2f} km"
                )

                c2.metric(
                    "Estimated Driving Time",
                    f"{route['duration_hours']:.1f} hours"
                )

                st.caption(
                    "Driving time excludes sightseeing, meal breaks, "
                    "traffic delays and overnight stops."
                )

                # Individual leg details.
                st.markdown("#### Route by City")

                legs_df = pd.DataFrame(route["legs"])

                legs_df = legs_df.rename(columns={
                    "from": "Starting City",
                    "to": "Next City",
                    "distance_km": "Distance (km)",
                    "duration_hours": "Driving Time (hours)"
                })

                st.dataframe(
                    legs_df,
                    use_container_width=True,
                    hide_index=True
                )

                # Build actual road path layers.
                path_layers = []

                for index, path in enumerate(route["paths"]):
                    path_layers.append(
                        pdk.Layer(
                            "PathLayer",
                            data=[{
                                "path": path,
                                "name": (
                                    f"{route['places'][index]} to "
                                    f"{route['places'][index + 1]}"
                                )
                            }],
                            get_path="path",
                            get_color=[23, 105, 210],
                            get_width=5,
                            width_min_pixels=4,
                            pickable=True
                        )
                    )

                # Add markers for all locations.
                marker_data = [
                    {
                        "name": point["name"],
                        "latitude": point["latitude"],
                        "longitude": point["longitude"]
                    }
                    for point in route["points"]
                ]

                marker_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=marker_data,
                    get_position="[longitude, latitude]",
                    get_radius=6500,
                    get_fill_color=[220, 45, 45],
                    get_line_color=[255, 255, 255],
                    line_width_min_pixels=2,
                    stroked=True,
                    pickable=True
                )

                path_layers.append(marker_layer)

                # Center map on the first city.
                view_latitude = sum(
                    point["latitude"] for point in route["points"]
                ) / len(route["points"])

                view_longitude = sum(
                    point["longitude"] for point in route["points"]
                ) / len(route["points"])

                view_state = pdk.ViewState(
                    latitude=view_latitude,
                    longitude=view_longitude,
                    zoom=5,
                    pitch=0
                )

                deck = pdk.Deck(
                    layers=path_layers,
                    initial_view_state=view_state,
                    tooltip={
                        "text": "{name}"
                    },
                    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
                )

                st.pydeck_chart(
                    deck,
                    use_container_width=True
                )

                st.caption(
                    "Blue line = road route. Red dots = city locations. "
                    "The map uses OpenStreetMap-based route data through OSRM."
                )

            # =============================================
            # BUDGET
            # =============================================

            st.subheader("💰 Estimated Travel Budget")

            distance_for_budget = 0.0

            if route and not route.get("error"):
                distance_for_budget = route["distance_km"]

            budget = calculate_budget(
                travel_mode=travel_mode,
                distance_km=distance_for_budget,
                travellers=int(travellers),
                duration_days=int(duration_days),
                fuel_price=float(fuel_price),
                mileage=float(mileage),
                bus_fare=float(bus_fare),
                food_per_day=float(food_per_day),
                hotel_per_night=float(hotel_per_night),
                hotel_rooms=int(hotel_rooms),
                other_expenses=float(other_expenses)
            )

            c1, c2 = st.columns(2)

            c1.metric(
                "Total Group Budget",
                f"₹{budget['total']:,.2f}"
            )

            c2.metric(
                "Estimated Cost Per Person",
                f"₹{budget['per_person']:,.2f}"
            )

            budget_df = pd.DataFrame({
                "Expense Category": [
                    "Transport",
                    "Food",
                    "Hotel",
                    "Other Expenses",
                    "Total"
                ],
                "Estimated Cost (Rs.)": [
                    budget["transport"],
                    budget["food"],
                    budget["hotel"],
                    budget["other"],
                    budget["total"]
                ]
            })

            st.dataframe(
                budget_df,
                use_container_width=True,
                hide_index=True
            )

            chart_df = pd.DataFrame({
                "Expense": [
                    "Transport",
                    "Food",
                    "Hotel",
                    "Other Expenses"
                ],
                "Cost (Rs.)": [
                    budget["transport"],
                    budget["food"],
                    budget["hotel"],
                    budget["other"]
                ]
            }).set_index("Expense")

            st.bar_chart(chart_df)

            if travel_mode == "Own Vehicle":
                st.info(
                    "Fuel cost assumes a return journey over the complete "
                    "multi-city route. Actual distance may vary depending "
                    "on detours and additional travel."
                )

            # =============================================
            # AI ITINERARY
            # =============================================

            st.subheader("🤖 Your AI Travel Itinerary")

            with st.spinner("Generating your travel itinerary..."):
                itinerary = generate_itinerary(
                    start=starting_location.strip(),
                    destinations=destinations,
                    travel_mode=travel_mode,
                    travel_date=travel_date,
                    duration_days=int(duration_days),
                    travellers=int(travellers),
                    budget=budget["total"],
                    route=route if route and not route.get("error") else None
                )

            st.markdown(itinerary)

            # =============================================
            # PDF EXPORT
            # =============================================

            st.subheader("📄 Download Your Travel Report")

            try:
                pdf_data = create_pdf(
                    start=starting_location.strip(),
                    destinations=destinations,
                    travel_mode=travel_mode,
                    travel_date=travel_date,
                    duration_days=int(duration_days),
                    travellers=int(travellers),
                    route=route if route and not route.get("error") else None,
                    budget=budget,
                    itinerary=itinerary
                )

                st.download_button(
                    label="Download Travel Plan (PDF)",
                    data=pdf_data,
                    file_name="AI_Smart_Travel_Plan.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            except Exception as error:
                st.error(
                    "PDF generation failed. Check the ReportLab setup "
                    "and try again."
                )


# =====================================================
# FOOTER
# =====================================================

st.markdown("""
<div class="app-footer">
    <p>
        <strong>AI Smart Travel Planner</strong><br>
        Built with Python, Streamlit, OpenStreetMap, OSRM and Groq AI.
    </p>
    <p>
        Distances, travel times, budgets and AI recommendations are
        estimates. Verify current fares, hotel prices, opening hours
        and travel conditions before departure.
    </p>
</div>
""", unsafe_allow_html=True)