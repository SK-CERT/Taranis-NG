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
 * Get current states for a specific entity
 * @param {string} entityType - The entity type
 * @param {string} entityId - The entity ID
 * @returns {Promise} API response with current entity states
 */
export function getEntityStates(entityType, entityId) {
  return ApiService.get(`/state/entities/${entityType}/${entityId}/states`);
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
 * Set states for a specific entity (backward compatibility - only uses first state)
 * @param {string} entityType - The entity type
 * @param {string} entityId - The entity ID
 * @param {Array} states - Array of state names (only first is used)
 * @param {Array} removeStates - Ignored (for backward compatibility)
 * @param {boolean} replaceAll - Ignored (for backward compatibility)
 * @returns {Promise} API response
 */
//export function setEntityStates(
//  entityType,
//  entityId,
//  states,
//  removeStates = [],
//  replaceAll = false
//) {
//  const state = states && states.length > 0 ? states[0] : null;
//  return setEntityState(entityType, entityId, state);
//}

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

/**
 * Replace entity state with a new state
 * @param {string} entityType - The entity type
 * @param {string} entityId - The entity ID
 * @param {string} state - New state name to set (replaces existing)
 * @returns {Promise} API response
 */
//export function replaceEntityStates(entityType, entityId, states) {
//  const state = states && states.length > 0 ? states[0] : null;
//  return setEntityState(entityType, entityId, state);
//}

/**
 * Add a single state to an entity (replaces any existing state)
 * @param {string} entityType - The entity type
 * @param {string} entityId - The entity ID
 * @param {string} stateName - The state name to set
 * @returns {Promise} API response
 */
//export function addEntityState(entityType, entityId, stateName) {
//  return setEntityState(entityType, entityId, stateName);
//}
