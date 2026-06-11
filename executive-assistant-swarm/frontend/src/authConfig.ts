import type { Configuration, PopupRequest } from "@azure/msal-browser";

/**
 * Configuration object to be passed to MSAL instance on creation. 
 * For a full list of MSAL.js configuration parameters, visit:
 * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md 
 */
export const msalConfig: Configuration = {
  auth: {
    // Replaced with the real Azure App Registration Client ID from backend/.env
    clientId: "30f40401-2bb1-4460-8208-5b22674761f0", 
    // Using the specific tenant ID from backend/.env instead of "common"
    authority: "https://login.microsoftonline.com/ec565537-4281-4573-9d9b-20d432ff6805",
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: "sessionStorage", // This configures where your cache will be stored
  }
};

/**
 * Scopes you add here will be prompted for user consent during sign-in.
 * By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
 * For more information about OIDC scopes, visit: 
 * https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
 */
export const loginRequest: PopupRequest = {
  scopes: ["User.Read", "Calendars.Read", "Calendars.ReadWrite", "Mail.Send"]
};
