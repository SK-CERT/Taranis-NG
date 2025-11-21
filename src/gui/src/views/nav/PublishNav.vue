<template>
    <Navigation
            :links  = "links"
            :icon   = "'mdi-send'"
    />
</template>

<script>
    import Navigation from "../../components/common/Navigation";

    export default {
        name: "AnalyzeNav",
        components: {
            Navigation
        },
        data: () => ({
            links: []
        })
    }
</script>
