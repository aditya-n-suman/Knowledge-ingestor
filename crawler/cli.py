import typer
app=typer.Typer()
@app.command()
def crawl(file:str):
    print(f"TODO: crawl {file}")

if __name__=="__main__":
    app()
