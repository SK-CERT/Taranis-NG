import ApiService from "@/services/api_service";

/**
 * Get available states for an entity type
 * @param {string} entityType - The entity type (e.g., 'report_item', 'news_item_aggregate', 'product')
 * @returns {Promise} API response with available states
 */
export function getEntityTypeStates(entityType) {
  return ApiService.get(`/state/entity-types/${entityType}/states`);
}
