const config = {
    baseUrl: 'https://sleep.projectswhynot.site//upload',
};


function checkFetchResult (res) {
    if (res.ok) {
        return res.json();
    } 
    else {
        Promise.reject(`Ошибка: ${res.status}`)
    }
}

function postFile (input) {
    return fetch(`${config.baseUrl}`, {
        method: 'POST',
        body: input.files[0]
    })
    .then((res) => {
        return checkFetchResult(res)
      })
}

export {postFile}