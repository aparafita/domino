# Author: Álvaro Parafita (parafita.alvaro@gmail.com)

class Gender:
    """
        Class to represent gender as ints.
        Definition of each gender is according to ISO/IEC 5218.

        An instance of Gender must be created passing it a converter function
        that takes any value and returns a string in 
            UNKNOWN, MALE, FEMALE, NOT_APPLICABLE
        Any Exception inside this method should be catched 
        and reraised as ValueError or TypeError accordingly.

        To use the class, call the instance directly with any value 
        to convert it to its int representation.
        To pass from an int to its ISO string representation, 
        use the 'name' function.
    """
    
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2
    NOT_APPLICABLE = 9
    

    def __init__(self, converter=None):
        if converter is None:
            def default_converter(x):
                if x in ['UNKNOWN', 'MALE', 'FEMALE', 'NOT_APPLICABLE']:
                    return x
                else:
                    raise ValueError(x)
                    
            converter = default_converter
                    
        self.converter = converter
        

    def __call__(self, gender):
        converted_gender = self.converter(gender)
            
        try:
            return getattr(self, converted_gender)
        except AttributeError:
            raise ValueError(
                'Gender "%s" became "%s", ' 
                'which is not recognised by Gender' % (
                    gender, converted_gender
                )
            )


    def name(self, gender):
        if type(gender) == int:
            if gender == Gender.UNKNOWN:
                return 'UNKNOWN'
            elif gender == Gender.MALE:
                return 'MALE'
            elif gender == Gender.FEMALE:
                return 'FEMALE'
            elif gender == Gender.NOT_APPLICABLE:
                return 'NOT_APPLICABLE'
            else:
                raise ValueError(gender)
        else:
            raise TypeError(gender)


Gender.default = Gender()


def SimpleGender(convert):
    def lower_dict_comparison(x):
        try:
            x = x.lower()
        except AttributeError:
            return 'UNKNOWN'

        return convert.get(x, 'UNKNOWN')

    return Gender(lower_dict_comparison)