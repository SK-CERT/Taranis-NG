import ApiService from "@/services/api_service";

/**
 * Get available states for an entity type
 * @param {string} entityType - The entity type (e.g., 'report_item', 'news_item_aggregate', 'product')
 * @returns {Promise} API response with available states
 */
export function getEntityTypeStates(entityType) {
  return ApiService.get(`/state/entity-types/${entityType}/states`);
}

/**
 * Set state for a specific entity (replaces any existing state)
 * @param {string} entityType - The entity type
 * @param {string} entityId - The entity ID
 * @param {string} state - State name to set (replaces current state)
 * @returns {Promise} API response
 */
export function setEntityState(entityType, entityId, state) {
  const data = {
    state: state
  };
  return ApiService.post(
    `/state/entities/${entityType}/${entityId}/states`,
    data
  );
}

/**
 * Remove current state from an entity
 * @param {string} entityType - The entity type
 * @param {string} entityId - The entity ID
 * @returns {Promise} API response
 */
export function removeEntityState(entityType, entityId) {
  const data = {
    remove_state: true
  };
  return ApiService.post(
    `/state/entities/${entityType}/${entityId}/states`,
    data
  );
}
