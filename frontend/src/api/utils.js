/**
 * Safely extract an array from an API response.
 * Handles paginated responses (with `results`) and plain arrays.
 * Returns an empty array if the data is not in the expected format.
 */
export const toArray = (res) => {
  const d = res.data?.results || res.data;
  return Array.isArray(d) ? d : [];
};
