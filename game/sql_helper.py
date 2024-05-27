def open_sql_file(path: str) -> str:
    """

    Parameters
    ----------
    path: str

    Returns
    -------
    str
    """
    try:
        with open(path, 'r') as file:
            sql_query = file.read()
        return sql_query
    except FileNotFoundError:
        print("The file was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
