/* Keep the national-number placeholder aligned with the selected CEMAC calling code. */
document.addEventListener("DOMContentLoaded", () => {
  const country = document.querySelector("[data-phone-country]");
  const number = document.querySelector("[data-phone-national]");
  if (!country || !number) return;

  const updateExample = () => {
    const option = country.options[country.selectedIndex];
    if (option?.dataset.example) number.placeholder = option.dataset.example;
  };

  country.addEventListener("change", updateExample);
  updateExample();
});
