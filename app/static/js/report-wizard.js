/* Client-side guidance shared by three-step SAVE-US report forms. */
document.addEventListener("DOMContentLoaded", () => {
  const wizard = document.querySelector("[data-report-wizard]");
  if (!wizard) return;

  const steps = Array.from(wizard.querySelectorAll("[data-report-step]"));
  const nextButton = wizard.querySelector("[data-report-next]");
  const backButton = wizard.querySelector("[data-report-back]");
  const finishButton = wizard.querySelector("[data-report-finish]");
  const cancelButton = wizard.querySelector("[data-report-cancel]");
  const stepLabel = wizard.querySelector("[data-report-step-label]");
  const progress = wizard.querySelector("[data-report-progress]");
  const progressText = wizard.querySelector("[data-report-progress-text]");
  const fileInput = wizard.querySelector("[data-report-photo]");
  const photoSelection = wizard.querySelector("[data-photo-selection]");
  const photoPreview = wizard.querySelector("[data-photo-preview]");
  const photoStatus = wizard.querySelector("[data-photo-status]");
  const photoName = wizard.querySelector("[data-photo-name]");
  const incidentCountry = wizard.querySelector("[data-incident-country]");
  const incidentRegion = wizard.querySelector("[data-incident-region]");
  const regionsData = document.getElementById("incident-regions-data");
  const geolocateButton = wizard.querySelector("[data-geolocate]");
  const geolocationStatus = wizard.querySelector("[data-geolocation-status]");
  const latitudeInput = wizard.querySelector("[data-latitude]");
  const longitudeInput = wizard.querySelector("[data-longitude]");
  const labels = JSON.parse(wizard.dataset.reportStepLabels || '["Identifying information", "Last-seen information", "Contact and circumstances"]');
  const totalSteps = Number(wizard.dataset.stepCount) || steps.length;
  const photoRequired = wizard.dataset.photoRequired !== "false";
  let hasPhoto = wizard.dataset.hasStoredPhoto === "true";
  let currentStep = 1;

  // Event location is deliberately separate from the reporter's profile location.
  if (incidentCountry && incidentRegion && regionsData) {
    const regionsByCountry = JSON.parse(regionsData.textContent);
    const refreshRegions = () => {
      const previousRegion = incidentRegion.value;
      const regions = regionsByCountry[incidentCountry.value] || [];
      incidentRegion.replaceChildren(new Option("Select region", ""));
      regions.forEach((region) => incidentRegion.add(new Option(region, region)));
      if (regions.includes(previousRegion)) incidentRegion.value = previousRegion;
    };
    incidentCountry.addEventListener("change", refreshRegions);
  }

  const updateStep = () => {
    currentStep = Math.min(Math.max(currentStep, 1), totalSteps);
    steps.forEach((step) => {
      step.hidden = Number(step.dataset.reportStep) !== currentStep;
    });
    stepLabel.textContent = `Step ${currentStep} of ${totalSteps} · ${labels[currentStep - 1]}`;
    const completion = (currentStep / totalSteps) * 100;
    progress.style.background = `linear-gradient(to right, var(--blue) ${completion}%, #d6e7fb ${completion}%)`;
    progressText.textContent = `${currentStep} / ${totalSteps}`;
    // Keep navigation visible as a progress cue, while disabling unavailable directions.
    backButton.hidden = false;
    backButton.disabled = currentStep === 1;
    nextButton.hidden = false;
    nextButton.disabled = currentStep === totalSteps;
    finishButton.hidden = currentStep !== totalSteps;
    cancelButton.hidden = currentStep !== 1;
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const currentStepIsValid = () => {
    const section = wizard.querySelector(`[data-report-step="${currentStep}"]`);
    const fields = Array.from(section.querySelectorAll("input, select, textarea"));
    const invalidField = fields.find((field) => !field.checkValidity());
    if (invalidField) {
      invalidField.reportValidity();
      invalidField.focus();
      return false;
    }
    if (currentStep === 1 && photoRequired && !hasPhoto) {
      photoStatus.textContent = "A recent photo is required";
      photoName.textContent = "Choose a PNG, JPG, or GIF image to continue.";
      photoSelection.classList.add("photo-selection-error");
      photoSelection.hidden = false;
      fileInput.focus();
      return false;
    }
    return true;
  };

  nextButton.addEventListener("click", () => {
    if (!currentStepIsValid()) return;
    if (currentStep >= totalSteps) return;
    currentStep = Math.min(currentStep + 1, totalSteps);
    updateStep();
  });

  backButton.addEventListener("click", () => {
    if (currentStep <= 1) return;
    currentStep = Math.max(currentStep - 1, 1);
    updateStep();
  });

  fileInput.addEventListener("change", () => {
    const selectedPhoto = fileInput.files[0];
    if (!selectedPhoto) return;
    hasPhoto = true;
    photoSelection.classList.remove("photo-selection-error");
    photoStatus.textContent = "Photo added";
    photoName.textContent = `${selectedPhoto.name} · ${(selectedPhoto.size / 1024 / 1024).toFixed(1)} MB`;
    photoPreview.src = URL.createObjectURL(selectedPhoto);
    photoPreview.hidden = false;
    photoSelection.hidden = false;
  });

  // Geolocation is opt-in. The mandatory manual location field keeps the form functional without it.
  if (geolocateButton && geolocationStatus && latitudeInput && longitudeInput) {
    geolocateButton.addEventListener("click", () => {
      if (!navigator.geolocation) {
        geolocationStatus.textContent = "Device location is unavailable. Please use the manual location field.";
        return;
      }
      geolocateButton.disabled = true;
      geolocationStatus.textContent = "Requesting device location…";
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => {
          latitudeInput.value = coords.latitude.toFixed(6);
          longitudeInput.value = coords.longitude.toFixed(6);
          geolocationStatus.textContent = "Device location added privately. You can still update the manual location.";
          geolocateButton.disabled = false;
        },
        () => {
          geolocationStatus.textContent = "Device location was not shared. Please use the manual location field.";
          geolocateButton.disabled = false;
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
      );
    });
  }

});
