from flask import Flask, request, render_template

# Initialize Flask app
app = Flask(__name__)

# Guardrail data with updated units and corrected concentrations
guardrail_data = {
    "Adrenaline": {
        "dosing_range": (0.05, 1.5),  # Accepted dose range (min, max)
        "unit": "mcg/kg/min",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [0.25, 1.25]},
            {"weight_range": "1-2.4kg", "dose_options": [0.75, 3]},
            {"weight_range": ">2.5kg", "dose_options": [1.25, 5]},
        ],
    },
    "Dobutamine": {
        "dosing_range": (5, 40),
        "unit": "mcg/kg/min",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [25, 100]},
            {"weight_range": "1-2.4kg", "dose_options": [75, 150]},
            {"weight_range": ">2.5kg", "dose_options": [100, 150]},
        ],
    },
    "Dopamine": {
        "dosing_range": (7.5, 20),
        "unit": "mcg/kg/min",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [10, 50]},
            {"weight_range": "1-2.4kg", "dose_options": [25, 100]},
            {"weight_range": ">2.5kg", "dose_options": [75, 200]},
        ],
    },
    "Midazolam low": {
        "dosing_range": (30, 120),
        "unit": "mcg/kg/hr",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [0.75, 3]},
            {"weight_range": "1-2.4kg", "dose_options": [1, 4]},
            {"weight_range": ">2.5kg", "dose_options": [1.5, 4.5]},
        ],
    },
    "Midazolam high": {
        "dosing_range": (120, 300),
        "unit": "mcg/kg/hr",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [2, 5]},
            {"weight_range": "1-2.4kg", "dose_options": [4, 12]},
            {"weight_range": ">2.5kg", "dose_options": [8, 20]},
        ],
    },
    "Morphine": {
        "dosing_range": (10, 40),
        "unit": "mcg/kg/hr",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [0.5, 1.5]},
            {"weight_range": "1-2.4kg", "dose_options": [1, 5]},
            {"weight_range": ">2.5kg", "dose_options": [2.5, 7.5]},
        ],
    },
    "Noradrenaline": {
        "dosing_range": (0.1, 1.5),
        "unit": "mcg/kg/min",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [0.3, 3]},
            {"weight_range": "1-2.4kg", "dose_options": [0.6, 3]},
            {"weight_range": ">2.5kg", "dose_options": [1.2, 6]},
        ],
    },
    "Prostaglandin": {
        "dosing_range": (5, 100),
        "unit": "ng/kg/min",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [25, 200]},
            {"weight_range": "1-2.4kg", "dose_options": [50, 0.3]},
            {"weight_range": ">2.5kg", "dose_options": [75, 0.5]},
        ],
    },
    "Tolazoline (PPHN)": {
        "dosing_range": (0.25, 2),
        "unit": "mg/kg/hr",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [50, 100]},
            {"weight_range": "1-2.4kg", "dose_options": [100, 200]},
            {"weight_range": ">2.5kg", "dose_options": [150, 300]},
        ],
    },
    "Vecuronium": {
        "dosing_range": (1, 1),
        "unit": "mcg/kg/min",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [1.5]},
            {"weight_range": "1-2.4kg", "dose_options": [4]},
            {"weight_range": ">2.5kg", "dose_options": [7.5]},
        ],
    },
    "Insulin": {
        "dosing_range": None,
        "unit": "mcg/kg/hr",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [5, 15]},
            {"weight_range": "1-2.4kg", "dose_options": [10, 25]},
            {"weight_range": ">2.5kg", "dose_options": [20, 50]},
        ],
    },
    "Rocuronium": {
        "dosing_range": (300, 600),
        "unit": "mcg/kg/hr",
        "concentrations": [
            {"weight_range": "<1kg", "dose_options": [20]},
            {"weight_range": "1-2.4kg", "dose_options": [35]},
            {"weight_range": ">2.5kg", "dose_options": [75]},
        ],
    },
}

def calculate_total_dose(dose, weight, per_minute=False):
    if per_minute:
        dose *= 60  # Convert mcg/kg/min to mcg/kg/hour if necessary
    return dose * weight * 24  # Total dose for 24 hours

def calculate_infusion(volume, concentration, total_dose):
    total_volume = total_dose / (concentration * volume)
    hourly_rate = total_volume / 24
    return total_volume, hourly_rate

@app.route("/", methods=["GET", "POST"])
def prescribe_infusion():
    results = []
    out_of_range_warning = False  # Track whether the dose is out of range
    error_message = ""
    
    if request.method == "POST":
        drug = request.form.get("drug")
        weight = float(request.form.get("weight"))
        dose = float(request.form.get("dose"))
        dose_unit = request.form.get("dose_unit")

        # Check if the drug is in the database
        if drug not in guardrail_data:
            return render_template("index.html", error="Drug not found in database.", guardrail_data=guardrail_data)
        
        # Retrieve drug info
        drug_info = guardrail_data[drug]
        dosing_range = drug_info["dosing_range"]
        unit = drug_info["unit"]
        
        # Check if the dose is within the accepted range
        if not (dosing_range[0] <= dose <= dosing_range[1]):
            out_of_range_warning = True
            error_message = f"The dose is out of the accepted range ({dosing_range[0]} - {dosing_range[1]} {unit})."

        # Handle the unit conversion for mcg/kg/min -> mcg/kg/hour
        if dose_unit == "mcg/kg/min" and unit == "mcg/kg/hour":
            dose *= 60  # Convert mcg/kg/min to mcg/kg/hour
        elif dose_unit == "ng/kg/min" and unit == "mcg/kg/min":
            dose /= 1000  # Convert ng/kg/min to mcg/kg/min

        # Calculate total dose
        total_dose = calculate_total_dose(dose, weight, per_minute=(dose_unit == "mcg/kg/min"))

        # Identify the concentration based on weight
        for conc in drug_info["concentrations"]:
            weight_range = conc["weight_range"]
            dose_options = conc["dose_options"]
            
            if (weight < 1 and weight_range == "<1kg") or \
               (1 <= weight <= 2.4 and weight_range == "1-2.4kg") or \
               (weight > 2.5 and weight_range == ">2.5kg"):
                for dose_option in dose_options:
                    total_volume, hourly_rate = calculate_infusion(25, dose_option, total_dose)
                    results.append({
                        "concentration": dose_option,
                        "total_volume": round(total_volume, 2),
                        "hourly_rate": round(hourly_rate, 2)
                    })
        
        return render_template("result.html", drug=drug, weight=weight, dose=dose, unit=unit,
                               results=results, dose_range=dosing_range,
                               out_of_range_warning=out_of_range_warning,
                               error_message=error_message, guardrail_data=guardrail_data)

    return render_template("index.html", guardrail_data=guardrail_data)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
