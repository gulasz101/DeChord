const envTabsUi = import.meta.env.VITE_ENABLE_TABS_UI;

export const ENABLE_TABS_UI = envTabsUi === "1" || envTabsUi === "true";
