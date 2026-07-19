/* Populate the primary-region selector from the local CEMAC dataset. */
document.addEventListener("DOMContentLoaded", () => {
  const countrySelect = document.querySelector("#country-code");
  const regionSelect = document.querySelector("#primary-region");
  const regionLabel = document.querySelector("#subdivision-label");
  const dataElement = document.querySelector("#cemac-data");

  if (!countrySelect || !regionSelect || !regionLabel || !dataElement) return;

  const countries = JSON.parse(dataElement.textContent);
  const initialRegion = window.SAVE_US_SELECTED_REGION;

  const populateRegions = (selectedRegion = "") => {
    const country = countries[countrySelect.value];
    regionLabel.textContent = "Primary " + country.type_subdivision;
    regionSelect.replaceChildren();
    country.subdivisions.forEach((subdivision) => {
      const option = new Option(
        subdivision.nom + " — " + subdivision.chef_lieu,
        subdivision.nom,
        false,
        subdivision.nom === selectedRegion,
      );
      regionSelect.add(option);
    });
  };

  populateRegions(initialRegion);
  countrySelect.addEventListener("change", () => populateRegions());
});
