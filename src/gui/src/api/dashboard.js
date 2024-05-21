import ApiService from "@/services/api_service";

export function getDashboardData() {
    return ApiService.getWithCancel('screenData', '/dashboard-data')
}