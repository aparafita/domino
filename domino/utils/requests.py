# Author: Álvaro Parafita (parafita.alvaro@gmail.com)

def raise_for_status(r):
    """ 
        Executes r.raise_for_status(), 
        but prints first the contents of the response
        if there's an error, to check any error messages
    """
    
    try:
        r.raise_for_status()
    except:
        try:
            print(r.json())
        except:
            print(r.text)
        
        raise