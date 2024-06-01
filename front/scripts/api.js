function waiter () {
    return fetch('https://sleep.projectswhynot.site/upload', {
        method: 'GET'
    })
    .then((res) => {
        if (res.ok) {
            window.location.href = "https://sleep.projectswhynot.site/results";
        }
    })
}

waiter()