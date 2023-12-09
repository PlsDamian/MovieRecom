from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx

app = FastAPI()
templates = Jinja2Templates(directory="templates")  # Assumes your templates directory is named "templates"

# Configuration
TMDB_API_KEY = 'd665a95831ba30d490fe8508abc540e8'
TMDB_API_BASE_URL = 'https://api.themoviedb.org/3'
MAX_RECURSION_DEPTH = 10  # Maximum depth for recursive calls
MAX_MOVIES_PER_GENRE = 10  # Maximum number of movies to fetch per genre


app.mount("/images", StaticFiles(directory="images"), name="images")


# API Endpoint to Render Home Template
@app.get("/", response_class=HTMLResponse)
async def render_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


# TMDb Movie Model
class TMDbMovie:
    def __init__(self, title: str, genre: str):
        self.title = title
        self.genre = genre


async def fetch_tmdb_movie_recommendations(genre_name: str, tmdb_api_key: str, depth=0):
    if depth > MAX_RECURSION_DEPTH:
        # Stop recursion after exceeding depth limit
        return []

    # Fetch the genre ID for the given genre name
    async with httpx.AsyncClient() as client:
        genre_response = await client.get(f'{TMDB_API_BASE_URL}/genre/movie/list', params={'api_key': tmdb_api_key})
        genre_data = genre_response.json()
        genre_id = next((genre['id'] for genre in genre_data['genres'] if genre['name'].lower() == genre_name.lower()), None)

    if genre_id is None:
        print(f"Genre ID not found for genre: {genre_name}")
        return []

    async with httpx.AsyncClient() as client:
        tmdb_response = await client.get(
            f'{TMDB_API_BASE_URL}/discover/movie',
            params={'api_key': tmdb_api_key, 'with_genres': genre_id}
        )

        try:
            tmdb_data = tmdb_response.json()
            print("TMDB API Response:", tmdb_data)

            # Fetch only a limited number of movies
            movies = tmdb_data.get('results', [])[:MAX_MOVIES_PER_GENRE]
            return [TMDbMovie(title=movie['title'], genre=genre_name) for movie in movies]

        except Exception as e:
            print(f"Error processing TMDB API response: {str(e)}")
            return []


# Function to Get TMDb Movie Recommendations based on Selected Genre
async def get_tmdb_recommendations_by_selected_genre(
    user_id: int, session: httpx.AsyncClient, tmdb_api_key: str, selected_genre: str
) -> dict:
    try:
        # Fetch TMDb movie recommendations for the selected genre
        recommended_movies = await fetch_tmdb_movie_recommendations(selected_genre, tmdb_api_key)

        return {"recommended_movies": recommended_movies}

    except Exception as e:
        print(f"An error occurred while fetching recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Dependency to inject the HTTP client for TMDB API calls
async def get_session():
    async with httpx.AsyncClient() as session:
        yield session


# API Endpoint to Get TMDb Movie Recommendations based on Selected Genre
@app.get("/tmdb_recommendations_selected_genre/{user_id}")
async def get_tmdb_recommendations_selected_genre_endpoint(
    user_id: int,
    selected_genre: str,
    session: httpx.AsyncClient = Depends(get_session),
    tmdb_api_key: str = Header(..., description="TMDb API Key"),
):
    return await get_tmdb_recommendations_by_selected_genre(user_id, session, tmdb_api_key, selected_genre)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
