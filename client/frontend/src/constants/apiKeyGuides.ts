export interface ApiKeyGuide {
  title: string;
  steps: string[];
}

export const API_KEY_GUIDES: Record<string, ApiKeyGuide> = {
  google: {
    title: "Google Gemini API Key",
    steps: [
      "Go to https://aistudio.google.com/",
      "Sign in with your Google account",
      'Click "Get API key" then "Create API key"',
      "Copy and save the key securely",
    ],
  },
  openai: {
    title: "OpenAI API Key",
    steps: [
      "Go to https://platform.openai.com/signup",
      "Create account and complete phone verification",
      'Add payment method in "Settings" > "Billing"',
      "Purchase prepaid credits (minimum $5)",
      'Go to "API keys" and click "+ Create new secret key"',
      "Copy and save the key securely",
      'Ensure "gpt-4o-mini" is enabled in your project settings',
    ],
  },
  anthropic: {
    title: "Anthropic Claude API Key",
    steps: [
      "Go to console.anthropic.com and sign up",
      'Set up billing in "Settings" > "Billing"',
      "Add payment method and purchase $5 minimum credits",
      'Go to "API Keys" and click "Create Key"',
      "Copy and save the key securely",
    ],
  },
  mistral: {
    title: "Mistral AI API Key",
    steps: [
      "Go to https://console.mistral.ai/ and sign up",
      "Create workspace if prompted",
      'Add payment method in "Billing"',
      'Go to "API Keys" and click "Create new key"',
      "Copy and save the key securely",
    ],
  },
  perplexity: {
    title: "Perplexity AI API Key",
    steps: [
      "Go to https://www.perplexity.ai/ and create an account",
      'Go to "Settings" > "API" tab',
      "Add payment method and purchase credits",
      'Click "Generate API Key"',
      "Copy and save the key securely",
    ],
  },
};
