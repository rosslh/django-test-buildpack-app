const URL_REGEX = /https?:\/\/[^\s<>()]+/g;
const WRAPPABLE_CHARS_REGEX = /([/.\-_?=&%#~])/g;
const ZWSP = '\u200B';

const extractUrls = (text: string): string[] => {
  return text.match(URL_REGEX) || [];
};

const addWrappableSpaces = (url: string): string => {
  return url.replace(WRAPPABLE_CHARS_REGEX, `$1${ZWSP}`);
};

const escapeRegExp = (string: string) => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
};

export const processWrappableUrls = (oldValue: string, newValue: string): [string, string] => {
  const oldUrls = extractUrls(oldValue);
  const newUrls = extractUrls(newValue);
  const commonUrls = oldUrls.filter((url) => newUrls.includes(url));

  let processedOldValue = oldValue;
  let processedNewValue = newValue;

  new Set(commonUrls).forEach((url) => {
    const wrappedUrl = addWrappableSpaces(url);
    const urlRegex = new RegExp(escapeRegExp(url), 'g');
    processedOldValue = processedOldValue.replace(urlRegex, wrappedUrl);
    processedNewValue = processedNewValue.replace(urlRegex, wrappedUrl);
  });

  return [processedOldValue, processedNewValue];
};
