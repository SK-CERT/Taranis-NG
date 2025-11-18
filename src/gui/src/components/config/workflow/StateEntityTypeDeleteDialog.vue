<template>
    <v-dialog v-model="value" max-width="500px" @click:outside="$emit('close')">
        <v-card>
            <v-card-title class="headline">{{ $t('workflow.state_workflow.delete_state_association') }}</v-card-title>
            <v-card-text>
                <div v-if="editedItem && editedItem.state">
                    {{ $t('workflow.state_workflow.delete_state_association_confirm') }}
                    <br><br>
                    <strong>{{ $t('workflow.state_workflow.entity_type') }}:</strong>
                    {{ $te('workflow.entity_types.' + editedItem.entity_type) ? $t('workflow.state_workflow.entity_types.' + editedItem.entity_type) : editedItem.entity_type }}
                    <br>
                    <strong>{{ $t('workflow.state_workflow.state') }}:</strong>
                    <v-icon :color="editedItem.state.color" small>{{ editedItem.state.icon }}</v-icon>
                    {{ $te('workflow.states.' + editedItem.state.display_name) ? $t('workflow.states.' + editedItem.state.display_name) : editedItem.state.display_name }}
                </div>
            </v-card-text>
            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="error" text @click="$emit('delete')">{{ $t('common.delete') }}</v-btn>
                <v-btn color="grey darken-1" text @click="$emit('close')">{{ $t('common.cancel') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script>
export default {
    name: "StateEntityTypeDeleteDialog",
    props: {
        value: Boolean,
        editedItem: Object
    }
}
</script>
